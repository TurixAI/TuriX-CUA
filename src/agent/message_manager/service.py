from __future__ import annotations

import logging
from typing import List, Optional, Type
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import (
	AIMessage,
	BaseMessage,
	HumanMessage,
	ToolMessage,
)
from langchain_openai import ChatOpenAI
from src.agent.message_manager.views import MessageHistory, MessageMetadata
from src.agent.prompts import AgentMessagePrompt, SystemPrompt
from src.agent.views import ActionResult, AgentOutput, AgentStepInfo

logger = logging.getLogger(__name__)


class MessageManager:
	def __init__(
		self,
		llm: BaseChatModel,
		task: str,
		action_descriptions: str,
		system_prompt_class: Type[SystemPrompt],
		max_input_tokens: int = 32000,
		estimated_tokens_per_character: int = 3,
		image_tokens: int = 800,
		max_error_length: int = 400,
		max_actions_per_step: int = 5,
	):
		self.llm = llm
		self.system_prompt_class = system_prompt_class
		self.max_input_tokens = max_input_tokens
		self.history = MessageHistory()
		self.task = task
		self.action_descriptions = action_descriptions
		self.ESTIMATED_TOKENS_PER_CHARACTER = estimated_tokens_per_character
		self.IMG_TOKENS = image_tokens
		self.max_error_length = max_error_length

		system_message = self.system_prompt_class(
			self.action_descriptions,
			max_actions_per_step=max_actions_per_step,
		).get_system_message()

		self._add_message_with_tokens(system_message)
		self.system_prompt = system_message
		task_message = self.task_instructions(task)
		self._add_message_with_tokens(task_message)
		self.tool_id = 1
		tool_calls = [
			{
				'name': 'AgentOutput',
				'args': {
					'current_state': {
						'evaluation_previous_goal': 'Unknown - No previous actions to evaluate.',
						'memory': 'Unknown - No previous actions to memorize.',
						'next_goal': 'Get user task',
						'reasoning': 'Unknown - Waiting for next goal',
						'information_stored': '',
						'improvement_proposal': ''
					},
					'action': [],
				},
				'id': str(self.tool_id),
				'type': 'tool_call',
			}
		]

		example_tool_call = AIMessage(
			content="",
			tool_calls=tool_calls
		)
		self._add_message_with_tokens(example_tool_call)
		tool_message = ToolMessage(
			content='macOS automation session started',
			tool_call_id=str(self.tool_id),
		)
		self._add_message_with_tokens(tool_message)
		self.tool_id += 1

	@staticmethod
	def task_instructions(task: str) -> HumanMessage:
		content = f'{task}. You should follow each step and evaluate the result of each step.'
		return HumanMessage(content=content)

	def add_state_message(
		self,
		state_content: list,
		result: Optional[List[ActionResult]] = None,
		step_info: Optional[AgentStepInfo] = None,
	) -> None:

		if result:
			for r in result:
				if r.include_in_memory:
					if r.extracted_content:
						msg = HumanMessage(content='Action result: ' + str(r.extracted_content))
						self._add_message_with_tokens(msg)
					if r.error:
						msg = HumanMessage(content='Action error: ' + str(r.error)[-self.max_error_length:])
						self._add_message_with_tokens(msg)
					result = None

		state_message = AgentMessagePrompt(
			state_content,
			result,
			max_error_length=self.max_error_length,
			step_info=step_info,
		).get_user_message()
		self._add_message_with_tokens(state_message)

	def _remove_last_state_message(self) -> None:
		while len(self.history.messages) > 2 and isinstance(self.history.messages[-1].message, HumanMessage):
			self.history.remove_message()

	def _remove_last_AIntool_message(self) -> None:
		while len(self.history.messages) > 2 and (isinstance(self.history.messages[-1].message, AIMessage) or isinstance(self.history.messages[-1].message, ToolMessage)):
			self.history.remove_message()

	def add_model_output(self, model_output: AgentOutput) -> None:
		tool_calls = [
			{
				'name': 'AgentOutput',
				'args': model_output.model_dump(mode='json', exclude_unset=True),
				'id': str(self.tool_id),
				'type': 'tool_call',
			}
		]

		msg = AIMessage(
			content='',
			tool_calls=tool_calls,
		)

		self._add_message_with_tokens(msg)
		tool_message = ToolMessage(
			content='',
			tool_call_id=str(self.tool_id),
		)
		self._add_message_with_tokens(tool_message)
		self.tool_id += 1

	def get_messages(self) -> List[BaseMessage]:
		msg = [m.message for m in self.history.messages]
		total_input_tokens = 0
		logger.debug(f'Messages in history: {len(self.history.messages)}:')
		for m in self.history.messages:
			total_input_tokens += m.metadata.input_tokens
			logger.debug(f'{m.message.__class__.__name__} - Token count: {m.metadata.input_tokens}')
		logger.debug(f'Total input tokens: {total_input_tokens}')
		return msg

	def _add_message_with_tokens(self, message: BaseMessage, position: int | None = None) -> None:
		token_count = self._count_tokens(message)
		metadata = MessageMetadata(input_tokens=token_count)
		self.history.add_message(message, metadata,position=position)


	def _count_text_tokens(self, text: str) -> int:
		"""Enhanced token counter with multi-modal support"""
		if '<image>' in text:
			return self.IMG_TOKENS + super()._count_text_tokens(text.replace('<image>',''))
		return super()._count_text_tokens(text)

	def _count_tokens(self, message: BaseMessage) -> int:
		"""Counts tokens for multi-modal messages including images"""
		tokens = 0
		
		if isinstance(message.content, list):
			for item in message.content:
				if isinstance(item, dict) and 'image_url' in item:
					tokens += self._count_image_tokens(item['image_url'])
				elif 'text' in item:
					tokens += self._count_text_tokens(item['text'])
		
		else:
			if '<image>' in message.content:
				tokens += self._handle_embedded_images(message.content)
			else:
				tokens += self._count_text_tokens(message.content)
		
		if hasattr(message, 'tool_calls'):
			tokens += self._count_text_tokens(str(message.tool_calls))
		
		return tokens
	
	def _count_image_tokens(self, image_url: dict) -> int:
		"""Calculate tokens for images based on OpenAI's token rules"""
		if not isinstance(self.llm, ChatOpenAI):
			return self.IMG_TOKENS 
		detail = image_url.get('detail', 'low')
		
		if detail == 'low':
			return 85  
		
		width = image_url.get('width', 0)
		height = image_url.get('height', 0)
		
		scaled_width, scaled_height = self._resize_dimensions(width, height)
		tile_count = ((scaled_width + 511) // 512) * ((scaled_height + 511) // 512)
		return 85 + (tile_count * 170)
	
	def _handle_embedded_images(self, text: str) -> int:
		"""Count tokens for <image> markers in text content"""
		tokens = 0
		image_count = text.count('<image>')
		tokens += image_count * self.IMG_TOKENS
		clean_text = text.replace('<image>', '')
		tokens += self._count_text_tokens(clean_text)
		return tokens
	
	def _resize_dimensions(self, width: int, height: int) -> tuple[int, int]:
		"""Resize logic matching OpenAI's image processing"""
		max_dim = 2048
		if max(width, height) > max_dim:
			ratio = max_dim / max(width, height)
			return (int(width * ratio), int(height * ratio))
		return (width, height)

	def _count_text_tokens(self, text: str) -> int:
		if isinstance(self.llm, ChatOpenAI):
			try:
				self.llm.disabled_params = {'parallel_tool_calls': None}
				tokens = self.llm.get_num_tokens(text)
			except Exception:
				tokens = len(text) // self.ESTIMATED_TOKENS_PER_CHARACTER
		else:
			tokens = len(text) // self.ESTIMATED_TOKENS_PER_CHARACTER
		return tokens

	def cut_messages(self):
		diff = self.history.total_tokens - self.max_input_tokens
		if diff <= 0:
			return None

		msg = self.history.messages[-1]
		if isinstance(msg.message.content, list):
			text = ''
			for item in msg.message.content:
				if 'image_url' in item:
					msg.message.content.remove(item)
					diff -= self.IMG_TOKENS
					msg.metadata.input_tokens -= self.IMG_TOKENS
					self.history.total_tokens -= self.IMG_TOKENS
					logger.debug(
						f'Removed image with {self.IMG_TOKENS} tokens - total tokens now: {self.history.total_tokens}/{self.max_input_tokens}'
					)
				elif 'text' in item and isinstance(item, dict):
					text += item['text']
			msg.message.content = text
			self.history.messages[-1] = msg

		if diff <= 0:
			return None

		proportion_to_remove = diff / msg.metadata.input_tokens
		if proportion_to_remove > 0.99:
			raise ValueError(
				f'Max token limit reached - history is too long - reduce the system prompt or task. '
				f'proportion_to_remove: {proportion_to_remove}'
			)
		logger.debug(
			f'Removing {proportion_to_remove * 100:.2f}% of the last message  {proportion_to_remove * msg.metadata.input_tokens:.2f} / {msg.metadata.input_tokens:.2f} tokens)'
		)

		content = msg.message.content
		characters_to_remove = int(len(content) * proportion_to_remove)
		content = content[:-characters_to_remove]
		self.history.remove_message(index=-1)
		msg = HumanMessage(content=content)
		self._add_message_with_tokens(msg)
		last_msg = self.history.messages[-1]
		logger.debug(
			f'Added message with {last_msg.metadata.input_tokens} tokens - total tokens now: {self.history.total_tokens}/{self.max_input_tokens} - total messages: {len(self.history.messages)}'
		)