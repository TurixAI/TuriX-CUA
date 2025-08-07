import logging
import os
import sys

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

	log_type = os.getenv('turix_LOGGING_LEVEL', 'info').lower()

	# Check if handlers are already set up
	if logging.getLogger().hasHandlers():
		return

	# Clear existing handlers
	root = logging.getLogger()
	root.handlers = []

	class BrowserUseFormatter(logging.Formatter):
		def format(self, record):
			if record.name.startswith('turix.'):
				record.name = record.name.split('.')[-2]
			return super().format(record)

	# Setup single handler for all loggers
	# For Windows, ensure UTF-8 encoding to handle Unicode characters like emojis
	if sys.platform == 'win32':
		import io
		# Wrap stdout with UTF-8 encoding to handle Unicode characters
		utf8_stdout = io.TextIOWrapper(
			sys.stdout.buffer, 
			encoding='utf-8', 
			errors='replace'
		)
		console = logging.StreamHandler(utf8_stdout)
	else:
		console = logging.StreamHandler(sys.stdout)

	# adittional setLevel here to filter logs
	if log_type == 'result':
		console.setLevel('RESULT')
		console.setFormatter(BrowserUseFormatter('%(message)s'))
	else:
		console.setFormatter(BrowserUseFormatter('%(levelname)-8s [%(name)s] %(message)s'))

	# Configure root logger only
	root.addHandler(console)

	# switch cases for log_type
	if log_type == 'result':
		root.setLevel('RESULT')  # string usage to avoid syntax error
	elif log_type == 'debug':
		root.setLevel(logging.DEBUG)
	else:
		root.setLevel(logging.INFO)

	# Configure turix logger
	turix_logger = logging.getLogger('turix')
	turix_logger.propagate = False  # Don't propagate to root logger
	turix_logger.addHandler(console)
	turix_logger.setLevel(root.level)  # Set same level as root logger

	logger = logging.getLogger('turix')
	logger.info('turix logging setup complete with level %s', log_type)
	# Silence third-party loggers
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
