# Copyright (c) Meta Platforms, Inc. and affiliates.
#
# This software may be used and distributed in accordance with
# the terms of the DINOv3 License Agreement.

import contextlib
import importlib
import inspect
import os
import sys
from pathlib import Path


@contextlib.contextmanager
def _load_modules_from_dir(dir_: str):
    sys.path.insert(0, dir_)
    yield
    sys.path.pop(0)


def load_custom_callable(module_path: str | Path, callable_name: str):
    module_full_path = os.path.realpath(module_path)
    assert os.path.exists(module_full_path), f"module {module_full_path} does not exist"
    module_dir, module_filename = os.path.split(module_full_path)
    module_name, _ = os.path.splitext(module_filename)

    with _load_modules_from_dir(module_dir):
        module = importlib.import_module(module_name)
        if inspect.getfile(module) != module_full_path:
            importlib.reload(module)
        callable_ = getattr(module, callable_name)

    return callable_


@contextlib.contextmanager
def change_working_dir_and_pythonpath(new_dir):
    old_dir = Path.cwd()
    new_dir = Path(new_dir).expanduser().resolve().as_posix()
    old_pythonpath = sys.path.copy()
    sys.path.insert(0, new_dir)
    os.chdir(new_dir)
    try:
        yield
    finally:
        os.chdir(old_dir)
        sys.path = old_pythonpath
