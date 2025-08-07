import logging
import os
import sys

from dotenv import load_dotenv

load_dotenv()


def addLoggingLevel(levelName, levelNum, methodName=None):

 if not methodName:
  methodName = levelName.lower()

 if hasattr(logging, levelName):
  raise AttributeError('{} already defined in logging module'.format(levelName))
 if hasattr(logging, methodName):
  raise AttributeError('{} already defined in logging module'.format(methodName))
 if hasattr(logging.getLoggerClass(), methodName):
  raise AttributeError('{} already defined in logger class'.format(methodName))

 def logForLevel(self, message, *args, **kwargs):
  if self.isEnabledFor(levelNum):
   self._log(levelNum, message, args, **kwargs)

 def logToRoot(message, *args, **kwargs):
  logging.log(levelNum, message, *args, **kwargs)

 logging.addLevelName(levelNum, levelName)
 setattr(logging, levelName, levelNum)
 setattr(logging.getLoggerClass(), methodName, logForLevel)
 setattr(logging, methodName, logToRoot)


def setup_logging():
    try:
        addLoggingLevel('RESULT', 35)
    except AttributeError:
        pass 

    log_type = os.getenv('TuriX_LOGGING_LEVEL', 'info').lower()

    if logging.getLogger().hasHandlers():
        return

    root = logging.getLogger()
    root.handlers = []

    class TuriXFormatter(logging.Formatter):
        def format(self, record):
            if record.name.startswith('turiX.'):
                record.name = record.name.split('.')[-2]
            return super().format(record)

    console = logging.StreamHandler(sys.stdout)

    if log_type == 'result':
        console.setLevel('RESULT')
        console.setFormatter(TuriXFormatter('%(message)s'))
    else:
        console.setFormatter(TuriXFormatter('%(levelname)-8s [%(name)s] %(message)s'))

    root.addHandler(console)

    if log_type == 'result':
        root.setLevel('RESULT')
    elif log_type == 'debug':
        root.setLevel(logging.DEBUG)
    else:
        root.setLevel(logging.INFO)

    turiX_logger = logging.getLogger('turiX')
    turiX_logger.propagate = False
    turiX_logger.addHandler(console)
    turiX_logger.setLevel(root.level)

    logger = logging.getLogger('turiX')
    logger.info('TuriX logging setup complete with level %s', log_type)
    for logger in [
        'WDM',
        'httpx',
        'selenium',
        'playwright',
        'urllib3',
        'asyncio',
        'langchain',
        'openai',
        'httpcore',
        'charset_normalizer',
        'anthropic._base_client',
        'PIL.PngImagePlugin',
    ]:
        third_party = logging.getLogger(logger)
        third_party.setLevel(logging.ERROR)
        third_party.propagate = False