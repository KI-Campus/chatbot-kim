from enum import Enum
from typing import Dict, Type

from actions.settings import load_config


class ResponseEnum(Enum):
	"""
	HELPER Enum class for automatically setting the enum's field-names as its value
	via the auto() initializer, see https://docs.python.org/3/library/enum.html#using-automatic-values
	"""
	def _generate_next_value_(name, start, count, last_values):
		return name


class ActionResponsesFiles(Enum):
	"""
	Enumeration for YAML files that contain response texts for actions

	CONVENTION: for each action-implementation file (*.py)
	<action>.py in actions/** , a (separate) response text file
	<action>_responses.py is defined in action_responses/**
	"""
	actions = 'actions_responses.yml'
	actions_recommender = 'actions_recommender_responses.yml'


def load_response_texts(file_name: str) -> Dict[str, Dict[str, str]]:
	"""
	load a YAML file with response text from subdirectory action_responses/**

	:param file_name: the name for the YAML file
	:return: the data dictionary corresponding to loaded YAML file
	"""
	return load_config(file_name, 'action_responses')


def get_response_texts(action: str, response_file: ActionResponsesFiles = ActionResponsesFiles.actions) -> Dict[str, str]:
	"""
	get the response texts for an Action-class loaded from an actions-implementation file

	:param action: the action name (as returned by its `name()` method)
	:param response_file: the actions-implementation file
	:return: the dictionary containing the response texts for action
	"""
	response_texts: Dict[str, Dict[str, str]] = load_response_texts(response_file.value)
	return response_texts[action]


def get_response(responses: Dict[str, str], response_field: Enum):
	"""
	get response for (Enum) `response_field` from dictionary `responses`

	:param responses: dictionary of response texts
	:param response_field: the Enum, for which to get the response text
	:return: the response text
	"""
	return responses[response_field.value]


def assert_responses_exist(responses: Dict[str, str], response_fields: Type[Enum]):
	"""
	HELPER verif that a dictionary with response-texts (loaded from a YAML file) contains
	all entries that are specified in the corresponding ResponseEnum

	NOTE will throw an Exception, if
	1) the Enum's field-names does not match its (string) value
	2) if the enum-entry has no corresponding field in the dictionary

	:param responses: the dictionary with the response texts
	:param response_fields: the ResponseEnum that specifies the expected fields/response text entries

	"""
	for label in response_fields:
		if label.name != label.value:
			raise Exception('invalid response enumeration {}: enum field name and value must be the same, but are {} = {}'.format(response_fields, label.value, label.name))
		if label.value not in responses:
			raise Exception('missing response text for {}: the text is specified in enumeration {}, but is missing in the response definitions (YAML file)'.format(label.value, response_fields))

		# print('  [{}] -> {}'.format(label, responses[label.value]))  # DEBUG
