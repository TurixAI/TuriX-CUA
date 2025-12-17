from __future__ import annotations
import asyncio
import base64
import io
import json
import logging
import os
import uuid
from pathlib import Path
import Quartz
import cv2
import numpy as np
import pickle
import faiss
import inspect
from typing import Any, Callable, Dict, List, Optional, Type, TypeVar
import re
from datetime import datetime
from dotenv import load_dotenv
from langchain_core.language_models.chat_models import BaseChatModel
from typing import Type
from collections import OrderedDict
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_openai import ChatOpenAI, AzureChatOpenAI          # OpenAI endpoints
from langchain_anthropic import ChatAnthropic                     # Claude
from langchain_google_genai import ChatGoogleGenerativeAI  
from langchain_core.messages import (
    BaseMessage,
)

from lmnr import observe
from openai import RateLimitError
from PIL import Image, ImageDraw, ImageFont
from pydantic import BaseModel, ValidationError
from src.agent.message_manager.service import MessageManager
from src.agent.prompts import (
    BrainPrompt_turix,
    ActorPrompt_turix,
)
from src.agent.views import (
    ActionResult,
    AgentError,
    AgentHistory,
    AgentHistoryList,
    AgentOutput,
    AgentStepInfo,
    AgentBrain
)
from src.agent.planner_service import Planner
from src.controller.service import Controller
from src.mac.tree import MacUITreeBuilder
from src.utils import time_execution_async
from src.agent.output_schemas import OutputSchemas
from src.agent.structured_llm import *

load_dotenv()
logger = logging.getLogger(__name__)

T = TypeVar('T', bound=BaseModel)

def screenshot_to_dataurl(screenshot):
    img_byte_arr = io.BytesIO()
    screenshot.save(img_byte_arr, format='PNG')
    base64_encoded = base64.b64encode(img_byte_arr.getvalue()).decode('utf-8')
    return f'data:image/png;base64,{base64_encoded}'

def to_structured(llm: BaseChatModel, Schema, Structured_Output) -> BaseChatModel:
    """
    Wrap *any* LangChain chat model with the right structured-output mechanism:

    • ChatOpenAI / AzureChatOpenAI  → bind(response_format=…)      (OpenAI style)
    • ChatAnthropic / ChatGoogleGenerativeAI → with_structured_output(…) (Claude/Gemini style)
    • anything else → returned unchanged
    """
    OPENAI_CLASSES: tuple[Type[BaseChatModel], ...] = (ChatOpenAI, AzureChatOpenAI)
    ANTHROPIC_OR_GEMINI: tuple[Type[BaseChatModel], ...] = (
        ChatAnthropic,
        ChatGoogleGenerativeAI,
    )

    if isinstance(llm, OPENAI_CLASSES):
        # OpenAI only: use the response_format param with your flattened schema
        return llm.bind(response_format=Schema)

    if isinstance(llm, ANTHROPIC_OR_GEMINI):
        # Claude & Gemini accept any schema textually → keep the nice Pydantic model
        return llm.with_structured_output(Structured_Output)

    # Fallback: no structured output
    return llm

class Agent:
    def __init__(
        self,
        task: str,
        brain_llm: BaseChatModel,
        actor_llm: BaseChatModel,
        short_memory_len : int,
        controller: Controller = Controller(),
        use_ui = False,
        planner_llm: Optional[BaseChatModel] = None,
        save_brain_conversation_path: Optional[str] = None,
        save_brain_conversation_path_encoding: Optional[str] = 'utf-8',
        save_actor_conversation_path: Optional[str] = None,
        save_actor_conversation_path_encoding: Optional[str] = 'utf-8',
        max_failures: int = 5,
        retry_delay: int = 10,
        max_input_tokens: int = 32000,
        resume = False,
        include_attributes: list[str] = [
            'title',
            'type',
            'name',
            'role',
            'tabindex',
            'aria-label',
            'placeholder',
            'value',
            'alt',
            'aria-expanded',
        ],
        max_error_length: int = 400,
        max_actions_per_step: int = 10,

        register_new_step_callback: Callable[['str', 'AgentOutput', int], None] | None = None,
        register_done_callback: Callable[['AgentHistoryList'], None] | None = None,
        tool_calling_method: Optional[str] = 'auto',
        agent_id: Optional[str] = None,
        knowledge_base_json: Optional[str] = None, # Path to the knowledge base JSON file
        screenshot_features_extractor: Optional[Callable[[str], np.ndarray]] = None, # model to extract features from screenshots
        embed_llm: Optional[BaseChatModel] = None, # embedding model for text
    ):
        self.wait_this_step = False
        if agent_id:
            self.agent_id = agent_id
        else:
            self.agent_id = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.task = task
        self.original_task = task
        self.resume = resume
        self.brain_llm = to_structured(brain_llm, OutputSchemas.BRAIN_RESPONSE_FORMAT, BrainOutput)
        self.actor_llm = to_structured(actor_llm, OutputSchemas.ACTION_RESPONSE_FORMAT, ActorOutput)
        self.planner_llm = to_structured(planner_llm, OutputSchemas.PLANNER_RESPONSE_FORMAT, PlannerOutput)

        self.save_actor_conversation_path = save_actor_conversation_path
        self.save_actor_conversation_path_encoding = save_actor_conversation_path_encoding

        self.save_brain_conversation_path = save_brain_conversation_path
        self.save_brain_conversation_path_encoding = save_brain_conversation_path_encoding

        self.include_attributes = include_attributes
        self.max_error_length = max_error_length
        self.screenshot_annotated = None
        self.short_memory_len = short_memory_len
        self.max_input_tokens = max_input_tokens
        self.save_temp_file_path = os.path.join(os.path.dirname(__file__), 'temp_files')
        self.use_ui = use_ui

        self.mac_tree_builder = MacUITreeBuilder()
        self.controller = controller
        self.max_actions_per_step = max_actions_per_step
        self.last_step_action = None
        self.goal_action_memory = OrderedDict()

        self.last_goal = None
        self.brain_history_memory = OrderedDict()
        self.status = "success"
        # Setup dynamic Action Model
        self._setup_action_models()
        # self._set_model_names()
        if self.planner_llm:
            self.planner = Planner(
                planner_llm=self.planner_llm,
                task=self.task,
                max_input_tokens=self.max_input_tokens,
            )

        # self.tool_calling_method = self.set_tool_calling_method(tool_calling_method)
        self.initiate_messages()
        self._last_result = None

        self.register_new_step_callback = register_new_step_callback
        self.register_done_callback = register_done_callback

        # Agent run variables
        self.history: AgentHistoryList = AgentHistoryList(history=[])
        self.n_steps = 1
        self.consecutive_failures = 0
        self.max_failures = max_failures
        self.retry_delay = retry_delay
        self._paused = False
        self._stopped = False
        self.short_memory = ''
        self.infor_memory = []
        self.last_pid = None
        self.ask_for_help = False

        if self.resume and not agent_id:
            raise ValueError("Agent ID is required for resuming a task.")
        self.save_temp_file_path = os.path.join(self.save_temp_file_path, f"{self.agent_id}")
        
        """ params for knowledge base """
        self.screenshot_features_extractor = screenshot_features_extractor # model to extract features from screenshots
        self.embed_model = embed_llm  # embedding model for text
        self.kb_match = None # store the matched knowledge base if matched
        self.knowledge_base_json = knowledge_base_json # Path to the knowledge base JSON file
        self.kb_steps = self._load_knowledge_base() if self.knowledge_base_json is not None else []  # list of knowledge base
        self.kb_match_Action = None # store the matched knowledge base action if matched
        self.kb_match_screenshot = None # store the matched knowledge base screenshot if matched
        self.similarity_threshold_text = 0.6 # threshold for text similarity matching
        self.similarity_threshold_image = 0.6 # threshold for image similarity matching
        self.memory = [] # memory to store the achieved goal of the last step
        

# -----------------------------------------------------[ below function is for knowledge base retrieval]-------------------------------------------------------------------------

    def _load_knowledge_base(self) -> List[Dict]:
        """load knowledge base from json file and build faiss index if not exists"""
        if os.path.exists(self.knowledge_base_json):
            with open(self.knowledge_base_json, 'r') as f:
                kb = json.load(f)
                steps = kb.get('steps', [])
                self.kb_steps = steps
                
                # 尝试加载已有索引，否则重新构建
                index_path = self.knowledge_base_json.replace('.json', '_faiss.index')
                embeddings_path = self.knowledge_base_json.replace('.json', '_embeddings.pkl')
                
                if os.path.exists(index_path) and os.path.exists(embeddings_path):
                    # 检查知识库是否有更新（通过条目数量简单判断）
                    with open(embeddings_path, 'rb') as pf:
                        saved_data = pickle.load(pf)
                        if saved_data.get('count') == len(steps):
                            self.kb_index = faiss.read_index(index_path)
                            self.kb_field_embeddings = saved_data['field_embeddings']
                            self.kb_image_features = saved_data['image_features']
                            logger.info(f"Loaded existing FAISS index with {self.kb_index.ntotal} entries")
                            return steps
                
                # 索引不存在或已过期，重新构建
                self._build_multimodal_index()
                return steps
        else:
            logger.warning(f"Knowledge base JSON not found at {self.knowledge_base_json}")
            self.kb_index = None
            self.kb_field_embeddings = None
            self.kb_image_features = None
            return []    

    def _get_text_normalized_embedding(self, text: str, description: str) -> np.ndarray:
        if not text:
            return np.zeros(3584)
        
        text = text.lower()  
        text = re.sub(r'[^\w\s]', '', text)  
        text = re.sub(r'\s+', ' ', text).strip() 

        prefixed_text = description + text  
        emb = self.embed_model.embed_query(prefixed_text) 
        emb = np.array(emb)
        norm = np.linalg.norm(emb)
        if norm == 0:
            return np.zeros(3584, dtype=np.float32)
        emb_norm = emb / norm
        if emb_norm.ndim == 1:
            emb_norm = emb_norm.reshape(1, -1)

        return emb_norm.astype(np.float32)

    def _build_multimodal_index(self) -> None:
        """
        build FAISS index for multimodal knowledge base:
        - store embeddings independently for each field (no concatenation, no addition)
        - store image features separately
        - calculate similarity separately and fuse weighted scores during retrieval
        """
        if not self.kb_steps:
            self.kb_index = None
            return
        
        logger.info(f"Building multimodal index for {len(self.kb_steps)} KB entries...")
        
        field_embeddings = {
            'task': [],
            'goal': [],
            'memory': [],
            'analysis': []
        }
        image_features = []
        
        for entry in self.kb_steps:
            task_emb = self._get_text_normalized_embedding(entry.get('task', ''), description="任务描述：")
            goal_emb = self._get_text_normalized_embedding(entry.get('step_goal', ''), description="步骤目标：")
            memory_emb = self._get_text_normalized_embedding(entry.get('memory', ''), description="已执行步骤：")
            analysis_emb = self._get_text_normalized_embedding(entry.get('screenshot_describe', ''), description="截屏分析：")
            
            screenshot_path = entry.get('screenshot', '')
            if screenshot_path and os.path.exists(screenshot_path):
                img_feature = self.screenshot_features_extractor._get_image_embedding(screenshot_path)
            else:
                img_feature = np.zeros(768, dtype=np.float32)
            
            field_embeddings['task'].append(task_emb.flatten())
            field_embeddings['goal'].append(goal_emb.flatten())
            field_embeddings['memory'].append(memory_emb.flatten())
            field_embeddings['analysis'].append(analysis_emb.flatten())
            image_features.append(img_feature.flatten())
        
        self.kb_field_embeddings = {k: np.array(v, dtype=np.float32) for k, v in field_embeddings.items()}
        self.kb_image_features = np.array(image_features, dtype=np.float32)
        
        self.kb_field_indices = {}
        for field_name, embeddings in self.kb_field_embeddings.items():
            if embeddings.shape[0] > 0:
                faiss.normalize_L2(embeddings)
                index = faiss.IndexFlatIP(embeddings.shape[1])  
                index.add(embeddings)
                self.kb_field_indices[field_name] = index
                logger.info(f"Built FAISS index for '{field_name}': {index.ntotal} vectors, dim={embeddings.shape[1]}")

        if self.kb_image_features.shape[0] > 0:
            faiss.normalize_L2(self.kb_image_features)
            self.kb_image_index = faiss.IndexFlatIP(self.kb_image_features.shape[1])
            self.kb_image_index.add(self.kb_image_features)
            logger.info(f"Built FAISS index for images: {self.kb_image_index.ntotal} vectors, dim={self.kb_image_features.shape[1]}")

        self._save_index()
        logger.info(f"Multimodal index built successfully")

    def _save_index(self) -> None:
        base_path = self.knowledge_base_json.replace('.json', '')
        
        for field_name, index in self.kb_field_indices.items():
            faiss.write_index(index, f"{base_path}_{field_name}.index")
        
        if hasattr(self, 'kb_image_index') and self.kb_image_index is not None:
            faiss.write_index(self.kb_image_index, f"{base_path}_image.index")
        
        embeddings_path = f"{base_path}_embeddings.pkl"
        with open(embeddings_path, 'wb') as f:
            pickle.dump({
                'count': len(self.kb_steps),
                'field_embeddings': self.kb_field_embeddings,
                'image_features': self.kb_image_features
            }, f)
        logger.info(f"Saved multimodal index to {base_path}_*.index")

    def _save_knowledge_base_match(self, goal: str, memory: str, candidates: List[Dict], top_k: int) -> None:
        """save the results of knowledge base matching"""
        os.makedirs('match', exist_ok=True)
        debug_info = {
            'query': {
                'task': self.task,
                'goal': goal,
                'memory': memory
            },
            'matches': [
                {
                    'task': c.get('task', ''),
                    'goal': c.get('step_goal', ''),
                    'score': c['score'],
                    'memory': c.get('memory', ''),
                    'analysis': c.get('screenshot_describe', ''),
                    'screenshot': c.get('screenshot', '')
                } for c in candidates[:top_k]
            ]
        }
        if not os.path.exists('match'):
            os.makedirs('match')
        with open(f'match/matched_{self.n_steps}.json', 'w', encoding='utf-8') as f:
            json.dump(debug_info, f, indent=2, ensure_ascii=False)

    def _search_knowledge_base(
        self, 
        current_goal: str, 
        current_memory: str, 
        current_screenshot_path: str, 
        current_screenshot_analysis: str,
        top_k: int = 3
    ) -> List[Dict]:
        """
        retrieve from multimodal knowledge base:
        - calculate similarity for each field independently
        - weighted fusion of scores to get final score
        - return top-k results
        """

        if not hasattr(self, 'kb_field_indices') or not self.kb_field_indices:
            logger.warning("Knowledge base indices not initialized")
            return []
        
        n_entries = len(self.kb_steps)
        if n_entries == 0:
            return []
        
        # 解析current_memory, 其实际参数为self.short_memory


        
        combined_scores = np.zeros(n_entries, dtype=np.float32)
        
        weights = {
            'task': 0.15,
            'goal': 0.35,
            'memory': 0.10,
            'analysis': 0.15,
            'image': 0.25
        }
        
        query_texts = {
            'task': (self.task, "任务描述："),
            'goal': (current_goal, "步骤目标："),
            'memory': (str(current_memory), "已执行步骤："),
            'analysis': (current_screenshot_analysis, "截屏分析：")
        }
        
        for field_name, (query_text, prefix) in query_texts.items():
            if field_name not in self.kb_field_indices:
                continue
            
            query_emb = self._get_text_normalized_embedding(query_text, description=prefix)
            query_emb = query_emb.flatten().reshape(1, -1).astype(np.float32)
            faiss.normalize_L2(query_emb)
            
            index = self.kb_field_indices[field_name]
            scores, indices = index.search(query_emb, n_entries)
            
            for i, idx in enumerate(indices[0]):
                if 0 <= idx < n_entries:
                    combined_scores[idx] += weights[field_name] * scores[0][i]
        
        if hasattr(self, 'kb_image_index') and self.kb_image_index is not None:
            if current_screenshot_path and os.path.exists(current_screenshot_path):
                img_query = self.screenshot_features_extractor._get_image_embedding(current_screenshot_path)
                img_query = img_query.flatten().reshape(1, -1).astype(np.float32)
                faiss.normalize_L2(img_query)
                
                img_scores, img_indices = self.kb_image_index.search(img_query, n_entries)
                
                for i, idx in enumerate(img_indices[0]):
                    if 0 <= idx < n_entries:
                        combined_scores[idx] += weights['image'] * img_scores[0][i]
        
        sorted_indices = np.argsort(combined_scores)[::-1] 
        
        candidates = []
        for idx in sorted_indices[:top_k]:
            score = combined_scores[idx]
            if score > self.similarity_threshold_text:  
                entry = self.kb_steps[idx].copy()
                entry['score'] = float(score)
                candidates.append(entry)
                logger.debug(f"KB match [{idx}]: score={score:.3f}, goal={entry.get('step_goal', '')[:50]}")
        
        self._save_knowledge_base_match( current_goal, str(current_memory), candidates, top_k)

        return candidates

    def point_position_transform(
        self,
        ref_image_path: str,
        query_image_path: str,
        ref_point: tuple,
        target_size: tuple = (1000, 1000),
        template_radius: int = 30,
    ) -> tuple:
        
        def _template_matching_search(query_img, template, rel_x, rel_y):
            """
            search for the corresponding point in the query image using local template matching
            the key is the point in the reference image, and we cut out a small region around this point as a template
            """
            query_gray = cv2.cvtColor(query_img, cv2.COLOR_BGR2GRAY)
            template_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
            
            best_val = -1
            best_loc = None
            best_scale = 1.0
            
            # 多尺度搜索
            scales = [0.9, 0.95, 1.0, 1.05, 1.1]
            
            for scale in scales:
                if scale != 1.0:
                    scaled_template = cv2.resize(template_gray, None, fx=scale, fy=scale)
                else:
                    scaled_template = template_gray
                
                # 确保模板不大于查询图像
                if scaled_template.shape[0] > query_gray.shape[0] or scaled_template.shape[1] > query_gray.shape[1]:
                    continue
                
                # 模板匹配
                result = cv2.matchTemplate(query_gray, scaled_template, cv2.TM_CCOEFF_NORMED)
                _, max_val, _, max_loc = cv2.minMaxLoc(result)
                
                if max_val > best_val:
                    best_val = max_val
                    best_loc = max_loc
                    best_scale = scale
            
            if best_val < 0.5:  # 匹配阈值
                logger.info(f"Warning: Low template match confidence: {best_val:.3f}")
                return None
            
            logger.info(f"Template match: confidence={best_val:.3f}, scale={best_scale:.2f}")
            
            # 计算对应点坐标（模板左上角 + 相对偏移 * 缩放）
            result_x = int(best_loc[0] + rel_x * best_scale)
            result_y = int(best_loc[1] + rel_y * best_scale)
            
            return [result_x, result_y]

        def _feature_matching_search(query_img, template, rel_x, rel_y, target_size):
            """
            search based on the local features with SIFT and FLANN (homography matrix)
            """
            query_gray = cv2.cvtColor(query_img, cv2.COLOR_BGR2GRAY)
            template_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
            
            sift = cv2.SIFT_create(nfeatures=500)
            
            kp1, des1 = sift.detectAndCompute(template_gray, None)
            kp2, des2 = sift.detectAndCompute(query_gray, None)
            
            if des1 is None or des2 is None or len(kp1) < 4 or len(kp2) < 4:
                logger.info("Warning: Insufficient features for local matching")
                return None
            
            FLANN_INDEX_KDTREE = 1
            index_params = dict(algorithm=FLANN_INDEX_KDTREE, trees=5)
            search_params = dict(checks=50)
            flann = cv2.FlannBasedMatcher(index_params, search_params)
            
            matches = flann.knnMatch(des1, des2, k=2)
            
            good_matches = []
            for match in matches:
                if len(match) == 2:
                    m, n = match
                    if m.distance < 0.7 * n.distance:
                        good_matches.append(m)
            
            if len(good_matches) < 4:
                logger.info(f"Warning: Only {len(good_matches)} good matches in local region")
                return None
            
            src_pts = np.float32([kp1[m.queryIdx].pt for m in good_matches]).reshape(-1, 1, 2)
            dst_pts = np.float32([kp2[m.trainIdx].pt for m in good_matches]).reshape(-1, 1, 2)
            
            H, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 3.0)
            
            if H is None:
                logger.info("Warning: Failed to compute local homography")
                return None
            
            inliers = mask.ravel().sum() if mask is not None else 0
            inlier_ratio = inliers / len(good_matches) if len(good_matches) > 0 else 0
            match_score = min(len(good_matches) / 20.0, 1.0) 
            confidence = inlier_ratio * match_score
            
            logger.info(f"Local feature match: matches={len(good_matches)}, inliers={inliers}, confidence={confidence:.3f}")
            
            ref_point_local = np.float32([[[rel_x, rel_y]]])
            query_point = cv2.perspectiveTransform(ref_point_local, H)
            
            result_x = int(query_point[0][0][0])
            result_y = int(query_point[0][0][1])
            

            if not (0 <= result_x < target_size[0] and 0 <= result_y < target_size[1]):
                logger.info(f"Warning: Result point ({result_x}, {result_y}) out of bounds")
                return None
            
            return [result_x, result_y]

        def find_corresponding_point_by_local_template(
            ref_image_path: str,
            query_image_path: str,
            ref_point: tuple,
            target_size: tuple = (1000, 1000),
            template_radius: int = 60,
            search_method: str = "template", 
        ) -> tuple:

            ref_img = cv2.imread(ref_image_path)
            query_img = cv2.imread(query_image_path)
            
            if ref_img is None or query_img is None:
                print("Error: Unable to read images")
                return None
            
            ref_img = cv2.resize(ref_img, target_size)
            query_img = cv2.resize(query_img, target_size)
            
            x, y = ref_point
            x1 = max(0, x - template_radius)
            y1 = max(0, y - template_radius)
            x2 = min(target_size[0], x + template_radius)
            y2 = min(target_size[1], y + template_radius)
            
            template = ref_img[y1:y2, x1:x2]
            
            if template.size == 0:
                print("Error: Template extraction failed")
                return None
            
            rel_x = x - x1
            rel_y = y - y1
            
            if search_method == "template":
                result_point = _template_matching_search(query_img, template, rel_x, rel_y)
            elif search_method == "feature":
                result_point = _feature_matching_search(query_img, template, rel_x, rel_y, target_size)
            else:
                print(f"Error: In {__file__}/{inspect.currentframe().f_code.co_name}() function, Unknown search method: {search_method}")
                return None
            
            return result_point

        result = find_corresponding_point_by_local_template(
            ref_image_path, query_image_path, ref_point,
            target_size=target_size,
            template_radius=template_radius,
            search_method="template"
        )
        
        if result is not None:
            return result
        
        result = find_corresponding_point_by_local_template(
            ref_image_path, query_image_path, ref_point,
            target_size=target_size,
            template_radius=template_radius,
            search_method="feature"
        )
        
        return result
    
# -----------------------------------------------------[ above function is for knowledge base retrieval]-------------------------------------------------------------------------

    def _set_model_names(self) -> None:
        self.chat_model_library = self.llm.__class__.__name__
        if hasattr(self.llm, 'model_name'):
            self.model_name = self.llm.model_name  # type: ignore
        elif hasattr(self.llm, 'model'):
            self.model_name = self.llm.model  # type: ignore
        else:
            self.model_name = 'Unknown'

    def set_tool_calling_method(self, tool_calling_method: Optional[str]) -> Optional[str]:
        if tool_calling_method == 'auto':
            if self.chat_model_library == 'ChatGoogleGenerativeAI':
                return None
            elif self.chat_model_library == 'ChatOpenAI':
                return 'function_calling'
            elif self.chat_model_library == 'AzureChatOpenAI':
                return 'function_calling'
            else:
                return None

    def _setup_action_models(self) -> None:
        """Setup dynamic action models from controller's registry"""
        self.ActionModel = self.controller.registry.create_action_model()
        self.AgentOutput = AgentOutput.type_with_custom_actions(self.ActionModel)

    def get_last_pid(self) -> Optional[int]:
        latest_pid = self.last_pid
        if self._last_result:
            for r in self._last_result:
                if r.current_app_pid:
                    latest_pid = r.current_app_pid
        return latest_pid

    def _update_short_memory(self) -> None:
        """
        Update memory content
        """

        memory_content = []
        sorted_steps = sorted(self.brain_history_memory.keys(), reverse=True)
        
        steps_to_keep = sorted_steps[:15]
        for step in sorted_steps:
            if step not in steps_to_keep:
                del self.brain_history_memory[step]

  
        for index, step in enumerate(sorted_steps):
            if step not in steps_to_keep:
                continue

            data = self.brain_history_memory[step]
            is_latest_step = (index == 0)
            
            if not is_latest_step:
                if 'current_state' in data and isinstance(data['current_state'], dict):
                    if 'task_progress' in data['current_state']:
                        del data['current_state']['task_progress']
                if 'task_progress' in data:
                    del data['task_progress']
     
            distance = self.n_steps - step
            if distance >= 5:
                if 'current_state' in data and 'analysis' in data:
                    summary = data['current_state']
                    self.brain_history_memory[step] = summary
                    data = summary 

        steps_to_render = sorted(steps_to_keep)
        for step in steps_to_render:
            data = self.brain_history_memory[step]
            distance = self.n_steps - step
            
            entry_str = ""
            if distance < 5:
                
                entry_str = f"Step {step} Brain Thought: {json.dumps(data, ensure_ascii=False)}"
            else:
                entry_str = f"Step {step} Brain Summary: {json.dumps(data, ensure_ascii=False)}"
            
            memory_content.append(entry_str)

        self.short_memory = "\n".join(memory_content)
        
    def save_memory(self) -> None:
        """
        Save the current memory to a file.
        """
        if not self.save_temp_file_path:
            return
        data = {
            "pid": self.get_last_pid(),
            "task": self.task,
            "next_goal": self.next_goal,
            "last_step_action": self.last_step_action,
            "infor_memory": self.infor_memory,
            # "brain_history_memory": self.brain_history_memory,
            'brain_history_memory': self.brain_history_memory,

            "step": self.n_steps
        }
        file_name = os.path.join(self.save_temp_file_path, f"memory.jsonl")
        os.makedirs(os.path.dirname(file_name), exist_ok=True) if os.path.dirname(file_name) else None
        with open(file_name, "w", encoding=self.save_brain_conversation_path_encoding) as f:
            if os.path.getsize(file_name) > 0:
                f.truncate(0)
            f.write(json.dumps(data, ensure_ascii=False, default=lambda o: list(o) if isinstance(o, set) else o) + "\n")

    def load_memory(self) -> None:
        """
        Load the current memory from a file.
        """
        if not self.save_temp_file_path:
            return
        file_name = os.path.join(self.save_temp_file_path, f".jsonl")
        if os.path.exists(file_name):
            with open(file_name, "r", encoding=self.save_brain_conversation_path_encoding) as f:
                lines = f.readlines()
            if len(lines) >= 1:
                data = json.loads(lines[-1])
                self.task = data.get("task", "")
                self.last_pid = data.get("pid", None)
                self.infor_memory = data.get("infor_memory", [])
                # self.state_memory = data.get("state_memory", None)
                self.brain_history_memory = data.get("brain_history_memory", OrderedDict())
                if self.brain_history_memory:
                    self.brain_history_memory = OrderedDict({int(k): v for k, v in self.brain_history_memory.items()})
                self._update_short_memory()
                self.last_step_action = data.get("last_step_action", None)
                self.next_goal = data.get("next_goal", "")
                self.n_steps = data.get("step", 1)
                logger.info(f"Loaded memory from {file_name}")

    @time_execution_async('--brain_step')
    async def brain_step(self,) -> dict:
        step_id = self.n_steps
        logger.info(f"\n📍 Step {self.n_steps}")
        prev_step_id = step_id - 1
        try:
            self.previous_screenshot = self.screenshot_annotated
            screenshot = self.mac_tree_builder.capture_screenshot()
            self.screenshot_annotated = screenshot
            screenshot.save(f'images/screenshot_{self.n_steps}.png')
            current_screenshot_path = f'images/screenshot_{self.n_steps}.png'
            if self.screenshot_annotated:
                screenshot_dataurl = screenshot_to_dataurl(self.screenshot_annotated)
            if self.previous_screenshot:
                previous_screenshot_dataurl = screenshot_to_dataurl(self.previous_screenshot)
            # Build content for state message
            if step_id >= 2:
                state_content = [
                    {
                        "type": "text",
                        "content": (
                            f"Previous step is {prev_step_id}.\n\n"
                            f"Necessary information remembered is:\n{self.infor_memory}\n\n"
                            f"Previous Actions Short History:\n{self.short_memory}\n\n"
                            f"Actions take by actor last step:\n{self.last_step_action}\n\n"
                        )
                    }
                ]
                if previous_screenshot_dataurl:
                    state_content.append({
                        "type": "image_url",
                        "image_url": {"url": previous_screenshot_dataurl},
                    })
                if screenshot_dataurl:
                    state_content.append({
                        "type": "image_url",
                        "image_url": {"url": screenshot_dataurl},
                    })
            else:
                state_content = [
                    {
                        "type": "text",
                        "content": (
                            f"This is the first step.\n\n"
                            f"You should provide a JSON with a well-defined goal based on images information. The other fields should be default value."
                        )
                    }
                ]
                if screenshot_dataurl:
                    state_content.append({
                        "type": "image_url",
                        "image_url": {"url": screenshot_dataurl},
                    })
            
            self.brain_message_manager._remove_last_state_message()
            self.brain_message_manager._remove_last_AIntool_message()
            self.brain_message_manager.add_state_message(state_content)
            brain_messages = self.brain_message_manager.get_messages()
            
            response = await self.brain_llm.ainvoke(brain_messages)
            brain_text = str(response.content)
            cleaned_brain_response = re.sub(r"^```(json)?", "", brain_text.strip())
            cleaned_brain_response = re.sub(r"```$", "", cleaned_brain_response).strip()
            logger.debug(f"[Brain] Raw text: {cleaned_brain_response}")
            parsed = json.loads(cleaned_brain_response)
            self._save_brain_conversation(brain_messages, parsed, step=self.n_steps)
            self.brain_history_memory[self.n_steps] = parsed
            self.next_goal = parsed['current_state']['next_goal']
            self.current_state = parsed['current_state']

            logger.info(f"Brain response: {parsed}")

            # ------------[ add for knowledge base retrieval ]----------------1
            self.current_screenshot_analysis = parsed['analysis']['analysis']
            self.task_progress = parsed['current_state']['task_progress']

            self.kb_match = self._search_knowledge_base(self.next_goal, self.memory, current_screenshot_path, self.current_screenshot_analysis)
            self.memory.append(self.next_goal)

            logger.info(f"self.next_goal: {self.next_goal} \n \
                         self.current_state: {self.current_state} \n \
                         self.kb_match: {self.kb_match} \n \
                         self.short_memory: {self.short_memory} \n \
                         current_screenshot_path: {current_screenshot_path}")
            
            if self.kb_match:
                converted_actions = []
                for act in self.kb_match[0]['actions']:
                    action_name = act['action']
                    params = act['parameters'] # just for action:”Click“，the paramentsers style is："parameters": {"position": [489,163]}
                    if action_name == 'Click':
                        logger.info(f"Original action parameters before transformation: {params}")
                        params['position'] = self.point_position_transform(ref_image_path=self.kb_match[0]['screenshot'], query_image_path=current_screenshot_path, ref_point=params['position']) 
                        logger.info(f"Transformed action parameters after transformation: {params}")
                    converted_actions.append({action_name: params})

                if 'position' in params and params['position'] is None:
                    self.kb_match = None
                    self.kb_match_actions = None
                    self.kb_match_screenshot = None
                    logger.debug(f"Knowledge base match found, but position could not be located on the current screen.")

                self.kb_match_actions = converted_actions
                self.kb_match_screenshot = self.kb_match[0]['screenshot']

                logger.info(f"Knowledge base match actions: {self.kb_match_actions}")
                logger.info(f"Knowledge base match found for goal '{self.next_goal}' with screenshot '{self.kb_match_screenshot}'")

        except Exception as e:
            logger.exception("[Brain] Unexpected error in brain_step.")
            return {"Brain_text": {"step_evaluate": "unknown", "reason": str(e)}}

    @time_execution_async("--actor_step")
    async def actor_step(self, step_info: Optional[AgentStepInfo] = None) -> None:
        step_id = self.n_steps
        state = "" # Default value
        model_output = None
        result: list[ActionResult] = []
        prev_step_id = step_id - 1
        try:
            #---------------------------
            # 1) Build the UI tree and capture a screenshot
            #---------------------------
            logger.debug(f'Last PID: {self.last_pid}')
            if self.use_ui:
                self.last_pid = self.get_last_pid()
                root = await self.mac_tree_builder.build_tree(self.last_pid)
                state = root._get_visible_clickable_elements_string() if root else "No UI tree found."
            else:
                state = ''
            self.save_memory()
            # ---------------------------
            # 3) Define the input message for the core agent
            # ---------------------------
            if self.n_steps >= 2:
                if self.use_ui:
                    state_content = [
                        {
                            "type": "text",
                            "content": f"Previous step is {prev_step_id}.\n\nYour goal to achieve in this step is: {self.next_goal}\n\nNecessary information remembered is: {self.infor_memory}\n\nCurrent UI state:\n{state}"
                        },
                        {
                            "type": "image_url",
                            "image_url": {"url": screenshot_to_dataurl(self.screenshot_annotated)},
                        }
                    ]
                else:
                    state_content = [
                        {
                            "type": "text",
                            "content": (
                                f"Necessary information remembered is: {self.infor_memory}\n\n"
                                f"Your goal to achieve in this step is: {self.next_goal}\n\n"   
                            )
                        },
                        {
                            "type": "image_url",
                            "image_url": {"url": screenshot_to_dataurl(self.screenshot_annotated)},
                        }
                    ]
            else:
                state_content = [
                    {
                        "type": "text",
                        "content": f"your goal to achieve in this step is: {self.next_goal}"
                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": screenshot_to_dataurl(self.screenshot_annotated)},
                    }
                ]
            
            if self.kb_match:
                kb_context_text = "The first screenshot is what you need to achieve your goal, the second one is the similar case from knowledge base. \
                    You may consider how the actions are taken for the second screenshot in the similar step, generate your actions to achieve the goal:\n"
                actions = [self.ActionModel(**action) for action in self.kb_match_actions]
                kb_context_text += f"The similar case:\n \
                        Task: {self.kb_match[0]['task']}\n \
                        Goal: {self.kb_match[0]['step_goal']}\n \
                        Memory: {self.kb_match[0]['memory']}\n \
                        Actions:\n{actions}\n\n"
                logger.info(f"Actions from KB match: {actions} ")
                kb_screenshot_dataurl = screenshot_to_dataurl(Image.open(self.kb_match_screenshot))
                state_content[0]["content"] += f"\n\n{kb_context_text}"
                state_content.append({
                    "type": "image_url",
                    "image_url": {"url": kb_screenshot_dataurl},
                })  
            else:
                logger.debug("No KB candidates found with score > 90%.")
            
            self.actor_message_manager._remove_last_AIntool_message()
            self.actor_message_manager._remove_last_state_message()
            self.actor_message_manager.add_state_message(state_content, step_info = step_info)
            
            actor_messages = self.actor_message_manager.get_messages()
            model_output, raw = await self.get_next_action(actor_messages)

            self.last_goal = self.next_goal
            if self.register_new_step_callback:
                self.register_new_step_callback(state, model_output, self.n_steps)
            self._save_actor_conversation(actor_messages, model_output, step=self.n_steps)

            self.actor_message_manager._remove_last_state_message()
            self.actor_message_manager.add_model_output(model_output)
            
            self.last_step_action = [action.model_dump(exclude_unset=True) for action in model_output.action] if model_output else []
            # join the self.state_memory and the self.last_goal

            result = await self.controller.multi_act(
                model_output.action,
                self.mac_tree_builder,
                action_valid=True
            )
            self._last_result = result
            if self.use_ui:
                for i in range(len(model_output.action)):
                    if 'open_app' in str(model_output.action[i]):
                        logger.debug(f'Found open_app action, building the tree again')
                        await self.mac_tree_builder.build_tree(self.get_last_pid())
            if len(self.last_step_action) == 0:
                self.wait_this_step = True
            elif 'wait' in str(self.last_step_action[0]):
                self.wait_this_step = True
            else:
                self.wait_this_step = False
            if self.last_step_action and not self.wait_this_step:

                self._update_short_memory()
                self.save_memory()

        except Exception as e:
            result = await self._handle_step_error(e)
            self._last_result = result
        finally:
            if result:
                self._make_history_item(model_output, state, result)
            if not self.wait_this_step:
                self.n_steps += 1

    async def _handle_step_error(self, error: Exception) -> list[ActionResult]:
        include_trace = logger.isEnabledFor(logging.DEBUG)
        error_msg = AgentError.format_error(error, include_trace=include_trace)
        prefix = f'❌ Result failed {self.consecutive_failures + 1}/{self.max_failures} times:\n '

        if isinstance(error, (ValidationError, ValueError)):
            logger.error(f'{prefix}{error_msg}')
            if 'Max token limit reached' in error_msg:
                # Possibly reduce tokens from history
                self.actor_message_manager.max_input_tokens -= 500
                logger.info(f'Reducing agent max input tokens: {self.actor_message_manager.max_input_tokens}')
                self.actor_message_manager.cut_messages()
            elif 'Could not parse response' in error_msg:
                error_msg += '\n\nReturn a valid JSON object with the required fields.'
            self.consecutive_failures += 1

        elif isinstance(error, RateLimitError):
            logger.warning(f'{prefix}{error_msg}')
            await asyncio.sleep(self.retry_delay)
            self.consecutive_failures += 1

        else:
            logger.error(f'{prefix}{error_msg}')
            self.consecutive_failures += 1

        return [ActionResult(error=error_msg, include_in_memory=True)]

    def _make_history_item(
        self,
        model_output: AgentOutput | None,
        state: str,
        result: list[ActionResult],
    ) -> None:
        history_item = AgentHistory(
            model_output=model_output,
            result=result,
            state=state,
        )
        self.history.history.append(history_item)

    @time_execution_async('--get_next_action')
    async def get_next_action(self, input_messages: list[BaseMessage]) -> AgentOutput:
        """
        Build a 'structured_llm' approach on top of self.llm. 
        Using the dynamic self.AgentOutput
        """        
        response: dict[str, Any] = await self.actor_llm.ainvoke(input_messages)
        logger.debug(f'LLM response: {response}')
        record = str(response.content)

        output_dict = json.loads(record)
        for i in range(len(output_dict['action'])):
            outer_key = list(output_dict['action'][i].keys())[0]
            inner_value = output_dict['action'][i][outer_key]
            if outer_key == "record_info":
                information_stored = inner_value.get("text", "None")
                self.infor_memory.append({f'Step {self.n_steps}, the information stored is: {information_stored}'})
        parsed: AgentOutput | None = AgentOutput(action=output_dict['action'])

        self._log_response(parsed)
        return parsed, record
    
    def _log_response(self, response: AgentOutput) -> None:
        if 'Success' in self.current_state["step_evaluate"]:
            emoji = '✅'
        elif 'Failed' in self.current_state["step_evaluate"]:
            emoji = '❌'
        else:
            emoji = '🤷'
        logger.info(f'{emoji} Eval: {self.current_state["step_evaluate"]}')
        logger.info(f'🧠 Memory: {self.brain_history_memory}')
        logger.info(f'🎯 Goal to achieve this step: {self.next_goal}')
        for i, action in enumerate(response.action):
            logger.info(f'🛠️  Action {i + 1}/{len(response.action)}: {action.model_dump_json(exclude_unset=True)}')
    
    def _save_brain_conversation(
        self,
        input_messages: list[BaseMessage],
        response: Any,
        step: int
    ) -> None:
        """
        Write all the Brain agent conversation (input messages + final AgentOutput)
        into a file: e.g. "brain_conversation_{step}.txt"
        """
        # If you do NOT want to save or no path provided, skip
        if not self.save_brain_conversation_path:
            return
        file_name = f"{self.save_brain_conversation_path}_brain_{step}.txt"
        os.makedirs(os.path.dirname(file_name), exist_ok=True) if os.path.dirname(file_name) else None

        with open(file_name, "w", encoding=self.save_brain_conversation_path_encoding) as f:
            # 1) Write input messages
            self._write_messages_to_file(f, input_messages)
            # 2) Write the final agent "response" (AgentOutput)
            if response is not None:
                self._write_response_to_file(f, response)

        logger.info(f"Brain conversation saved to: {file_name}")

    def _save_actor_conversation(
        self,
        input_messages: list[BaseMessage],
        response: Any,
        step: int
    ) -> None:
        """
        Write all the Actor agent conversation (input messages + final AgentOutput)
        into a file: e.g. "actor_conversation_{step}.txt"
        """
        # If you do NOT want to save or no path provided, skip
        if not self.save_actor_conversation_path:
            return
        file_name = f"{self.save_actor_conversation_path}_actor_{step}.txt"
        os.makedirs(os.path.dirname(file_name), exist_ok=True) if os.path.dirname(file_name) else None

        with open(file_name, "w", encoding=self.save_actor_conversation_path_encoding) as f:
            # 1) Write input messages
            self._write_messages_to_file(f, input_messages)
            # 2) Write the final agent "response" (AgentOutput)
            if response is not None:
                self._write_response_to_file(f, response)

        logger.info(f"Actor conversation saved to: {file_name}")

    def _write_messages_to_file(self, f: Any, messages: list[BaseMessage]) -> None:
        """
        For each message, write it out in a human-readable format.
        Or adapt your existing logic from _write_messages_to_file.
        """
        for message in messages:
            f.write(f"\n{message.__class__.__name__}\n{'-'*40}\n")
            if isinstance(message.content, list):
                for item in message.content:
                    if isinstance(item, dict):
                        if item.get('type') == 'text':
                            txt = item.get('content') or item.get('text', '')
                            f.write(f"[Text Content]\n{txt.strip()}\n\n")
                        elif item.get('type') == 'image_url':
                            image_url = item['image_url']['url']
                            f.write(f"[Image URL]\n{image_url[:100]}...\n\n")
            else:
                # If it's a string or something else:
                f.write(f"{str(message.content)}\n\n")
            f.write('\n' + '='*60 + '\n')

    def _write_response_to_file(self, f: Any, response: Any) -> None:
        """
        If the AgentOutput is JSON-like, you can do:
        """
        f.write('RESPONSE\n')
        # If it's an AgentOutput, you might do:
        #   f.write(json.dumps(json.loads(response.model_dump_json(exclude_unset=True)), indent=2))
        # Otherwise just string-ify it:
        f.write(str(response) + '\n')

        f.write('\n' + '='*60 + '\n')

    def _log_agent_run(self) -> None:
        logger.info(f'🚀 Starting task: {self.task}')

    async def run(self, max_steps: int = 100) -> AgentHistoryList:
        try:
            self._log_agent_run()

            if self.planner_llm and not self.resume:
                await self.edit()

            for step in range(max_steps):
                if self.resume:
                    self.load_memory()
                    self.resume = False
                if self._too_many_failures():
                    break
                if not await self._handle_control_flags():
                    break

                await self.brain_step()
                await self.actor_step()

                if self.history.is_done():
                    logger.info('✅ Task completed successfully')
                    if self.register_done_callback:
                        self.register_done_callback(self.history)
                    break
                await asyncio.sleep(2)  # Wait before next step
            else:
                logger.info('❌ Failed to complete task in maximum steps')

            return self.history
        except Exception:
            logger.exception('Error running agent')
            raise

    async def edit(self):
        response = await self.planner.edit_task()
        self._set_new_task(response)

    PREFIX = "The overall user's task is: "
    SUFFIX = "The step by step plan is: "

    def _set_new_task(self, generated_plan: str) -> None:
        """
        Build the final task string:
            "The overall plan is: <original task>\n\n<generated plan>"
        and update every MessageManager in one go.
        """
        if generated_plan.startswith(self.PREFIX):
            final_task = generated_plan
        else:
            final_task = f"{self.PREFIX}{self.original_task}\n{self.SUFFIX}\n{generated_plan}"
        self.task = final_task
        self.initiate_messages()

    def _too_many_failures(self) -> bool:
        if self.consecutive_failures >= self.max_failures:
            logger.error(f'❌ Stopping due to {self.max_failures} consecutive failures')
            return True
        return False

    async def _handle_control_flags(self) -> bool:
        if self._stopped:
            logger.info('Agent stopped')
            return False

        while self._paused:
            await asyncio.sleep(0.2)
            if self._stopped:
                return False

        return True

    def save_history(self, file_path: Optional[str | Path] = None) -> None:
        if not file_path:
            file_path = 'AgentHistory.json'
        self.history.save_to_file(file_path)

    def initiate_messages(self):
        self.brain_message_manager = MessageManager(
            llm=self.brain_llm,
            task=self.task,
            action_descriptions=self.controller.registry.get_prompt_description(),
            system_prompt_class=BrainPrompt_turix, # Typically your SystemPrompt
            max_input_tokens=self.max_input_tokens,
            include_attributes=self.include_attributes,
            max_error_length=self.max_error_length,
            max_actions_per_step=self.max_actions_per_step,
            give_task=True
        )
        self.actor_message_manager = MessageManager(
            llm=self.actor_llm,
            task=self.task,
            action_descriptions=self.controller.registry.get_prompt_description(),
            system_prompt_class=ActorPrompt_turix, # Typically your SystemPrompt
            max_input_tokens=self.max_input_tokens,
            include_attributes=self.include_attributes,
            max_error_length=self.max_error_length,
            max_actions_per_step=self.max_actions_per_step,
            give_task=False
        )
