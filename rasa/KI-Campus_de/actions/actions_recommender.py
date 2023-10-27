from enum import auto
from typing import Text, Dict, Any, List, Optional
from urllib import parse

from rasa_sdk import Action, Tracker
from rasa_sdk.events import SlotSet

import requests
import json

from rasa_sdk import FormValidationAction
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import Restarted
from rasa_sdk.types import DomainDict

from .settings import get_recommender_config
from .responses import get_response_texts, assert_responses_exist, ResponseEnum, get_response, ActionResponsesFiles


class ActionRestart(Action):

	def name(self) -> Text:
		return "action_restart"

	async def run(
		self, dispatcher, tracker: Tracker, domain: Dict[Text, Any]
	) -> List[Dict[Text, Any]]:

		# custom behavior
		dispatcher.utter_message(response="utter_restart")

		return [Restarted()]


class ActionCheckLogin(Action):

	def name(self) -> Text:
		return "action_check_login"

	def run(self, dispatcher: CollectingDispatcher,
			tracker: Tracker,
			domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

		current_state = tracker.current_state()
		is_logged_in = tracker.get_slot('user_login')
		if is_logged_in:
			# print('ActionCheckLogin[sender_id="{0}"]: ALREADY LOGGED IN, User ID {1}'.format(current_state['sender_id'], tracker.get_slot('user_id')), '\n')  # DEBUG
			return []

		token = current_state['sender_id']
		r = requests.get('https://learn.ki-campus.org/bridges/chatbot/user',
						 headers={
							 "content-type": "application/json",
							 "Authorization": 'Bearer {0}'.format(token)
						 })
		status = r.status_code

		# print('ActionCheckLogin[sender_id="{0}"]: status_code '.format(token), r.status_code, ', headers: ', r.headers, ', content: ', json.loads(r.content), '\n')  # DEBUG

		if status == 200:
			response = json.loads(r.content)
			user_id: Optional[str] = None
			if 'id' in response:  # FIXME use SAML ID when available
				user_id = response['id']
			return [SlotSet("user_login", True), SlotSet("user_id", user_id)]
		# elif status == 401:  # Status-Code 401 not authorized

		return [SlotSet("user_login", False), SlotSet("user_id", None)]


class ActionFetchProfile(Action):

	def name(self) -> Text:
		return "action_fetch_profile"

	def run(self, dispatcher: CollectingDispatcher,
			tracker: Tracker,
			domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

		enrollments: Optional[List[any]] = None
		current_state = tracker.current_state()
		token = current_state['sender_id']
		r = requests.get('https://learn.ki-campus.org/bridges/chatbot/my_courses',
						 headers={
							 "content-type": "application/json",
							 "Authorization": 'Bearer {0}'.format(token)
						 })
		status = r.status_code
		if status == 200:
			response = json.loads(r.content)
			if len(response) < 1:
				enrollments = []
			else:
				# for course in response:
				# 	enrollments.append(course)
				enrollments = response  # TODO [russa] only store part of data? e.g. only the ID or course_code?
		# elif status == 401:  # Status-Code 401 not authorized
		# 	enrollments = None
		# else:  # Other Stati
		# 	enrollments = None

		# # TEST values:
		# # TODO for these, would need to query KIC endpoint https://ki-campus.org/kic_api/users/<kic user id>
		# course_visits = ["Big Data Analytics"]
		# search_terms = ["KI", "Machine Learning"]
		course_visits = []
		search_terms = []
		# print('ActionFetchProfile: enrollments ', enrollments, ' | course_visits ', course_visits, ' | search_terms ', search_terms, '\n')  # DEBUG

		return [SlotSet("enrollments", enrollments), SlotSet("course_visits", course_visits), SlotSet("search_terms", search_terms)]

###################################
# RECOMMENDER
###################################

class ActionGetLearningRecommendation(Action):
	class Responses(ResponseEnum):
		no_recommendations_found = auto()
		found_recommendations = auto()
		"""
		text found_recommendations has 1 parameter: 
        * parameter {0}: total number (int) of found course recommendations
		"""
		found_recommendations_single = auto()
		"""
		text found_recommendations_single has 1 parameter: 
        * parameter {0}: total number (int) of found course recommendations
		"""
		found_course_item = auto()
		"""
		text found_course_item has 2 parameters:  
        * parameter {0}: the title of the course
        * parameter {1}: the URL-parameter /-ID for the course
		"""
		found_course_item_without_code = auto()
		"""
		text found_course_item_without_code has 2 parameters:  
        * parameter {0}: the title of the course
        * parameter {1}: URL-encoded string for the title of the course
		"""
		found_recommendations_more_single = auto()
		"""
		text found_recommendations_more_single has 1 parameter:
        * parameter {0}: number (int) of found, additional course recommendations (that are not shown yet)
		"""
		found_recommendations_more_multiple = auto()
		"""
		text found_recommendations_more_multiple has 1 parameter:
        * parameter {0}: number (int) of found, additional course recommendations (that are not shown yet)
		"""
		error_401 = auto()
		error_404 = auto()
		error_500 = auto()
		error_unknown = auto()
		"""
		text error_unknown has 1 parameter:
        * parameter {0}: the (text) content of the error message
		"""
		debug_error = auto()
		"""
		text debug_error has 3 parameters:
        * parameter {0}: the (HTTP) status code of the error message
        * parameter {1}: the (HTTP) headers of the error message
        * parameter {2}: the body/content of (HTTP) error message
		"""
		debug_recommendation_parameters = auto()
		"""
		text debug_recommendation_parameters has 1 parameter:
        * parameter {0}: string/description for the course recommendation/filter parameters
		"""

	responses: Dict[str, str]

	service_url: str
	service_token: str

	def __init__(self):
		self.responses = get_response_texts(self.name(), ActionResponsesFiles.actions_recommender)
		assert_responses_exist(self.responses, self.Responses)

		# NOTE will print error message if file or fields are missing:
		recommender_config = get_recommender_config()
		self.service_url = recommender_config['url']
		self.service_token = recommender_config['token']

		# DEBUG output
		# if recommender_config and recommender_config['url'] and recommender_config['token']:
		# 	print("\n  endpoint config: {0}\n".format(recommender_config))
		# else:
		# 	print("\n  endpoint config: NO CONFIGURATION FOR RECOMMENDER (recommender_api)\n")

	def name(self) -> Text:
		return "action_get_learning_recommendation"

	def run(self, dispatcher: CollectingDispatcher,
			tracker: Tracker,
			domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

		language = str(tracker.get_slot("language"))
		topic = str(tracker.get_slot("topic"))
		level = str(tracker.get_slot("level"))
		max_duration_str = tracker.get_slot("max_duration")  # int(tracker.get_slot("max_duration"))
		certificate = str(tracker.get_slot("certificate"))
		enrollments = tracker.get_slot("enrollments")
		course_visits = tracker.get_slot("course_visits")
		search_terms = tracker.get_slot("search_terms")

		if enrollments:
			enrollments = [course['course_code'] for course in enrollments]

		# to do: maybe option 2 implement after delete slot value

		# DEBUG: show search/filter parameters
		# debug_info_msg = "\n  language {0} | topic {1} | level {2} | max_duration {3} | certificate {4} | " \
		# 				 "enrollments {5} | course_visits {6} | search_terms {7}\n".format(
		# 					language, topic, level, max_duration_str, certificate, enrollments, course_visits, search_terms
		# 				 )
		# debug_params = get_response(self.responses, self.Responses.debug_recommendation_parameters).format(debug_info_msg)
		# dispatcher.utter_message(text=debug_params)

		r = requests.get('{0}filtered_recommendation_learnings/'.format(self.service_url),
			headers={
				"content-type": "application/json",
				"Authorization": 'Token {0}'.format(self.service_token),
			},
			params={
				"language": language,
				"topic": topic,
				"level": level,
				"max_duration": max_duration_str,  # str(max_duration),
				"certificate": certificate,
				"enrollments": enrollments,
				"course_visits": course_visits,
				"search_terms": search_terms,
			})
		status = r.status_code
		response: Optional[List] = None
		if status == 200:
			response = json.loads(r.content)
			if len(response) < 1:
				dispatcher.utter_message(get_response(self.responses, self.Responses.no_recommendations_found))
			else:
				size = len(response)
				limit = min(size, 3)
				dispatcher.utter_message(get_response(self.responses, self.Responses.found_recommendations_single).format(size)) if size == 1 else dispatcher.utter_message(get_response(self.responses, self.Responses.found_recommendations).format(size))
				course_label = get_response(self.responses, self.Responses.found_course_item)
				course_label_without_code = get_response(self.responses, self.Responses.found_course_item_without_code)
				# DISABLED [russa] for consistency, do not use buttons, but normal (link) utterances
				#          TODO maybe change to buttons again, when we allow selecting a course for enrolling
				# button_group = []
				for course in response[0:limit]:
					title = course['name']
					url_param = course['course_code']
					# NOTE [russa] course_code is sometimes empty ...
					# WORKAROUND: if course_code is not available, create link for searching by course title
					if url_param:
						message = course_label.format(title, url_param)
					else:
						message = course_label_without_code.format(title, parse.quote_plus(title))
					# DISABLED [russa] for consistency, do not use buttons, but normal (link) utterances:
					# # NOTE [russa]: disabled setting a payload with the course-title, since there is no real
					# #                interaction, if payload were to be triggered here
					# btn_payload = ''  # '{0}'.format(title)  # TODO enable if/when enrolling in courses is implemented
					# button_group.append({"title": message, "payload": btn_payload})
					dispatcher.utter_message(message)

				# # DISABLED [russa] for consistency, do not use buttons, but normal (link) utterances:
				# dispatcher.utter_message(text=" ", buttons=button_group)  # NOTE [russa] non-empty message as WORKAROUND for BUG in socketio-adapter (rasa v3.0-v3.2)

				if limit < size:
					rest = size - limit
					msg_type = self.Responses.found_recommendations_more_single if rest == 1 else self.Responses.found_recommendations_more_multiple
					dispatcher.utter_message(get_response(self.responses, msg_type).format(rest))

		elif status == 401:  # Status-Code 401 Unauthorized: wrong access token setting in kic_recommender.yml!
			dispatcher.utter_message(get_response(self.responses, self.Responses.error_401))
			# DEBUG:
			# dispatcher.utter_message(get_response(self.responses, self.Responses.debug_error).format(str(r.status_code), str(r.headers), str(r.content)))
		elif status == 404:  # Status-Code 404 None
			dispatcher.utter_message(get_response(self.responses, self.Responses.error_404))
			# DEBUG:
			# dispatcher.utter_message(get_response(self.responses, self.Responses.debug_error).format(str(r.status_code), str(r.headers), str(r.content)))
		elif status == 500:  # Status-Code 500 Invalid Parameter
			dispatcher.utter_message(get_response(self.responses, self.Responses.error_500))
			# DEBUG:
			# dispatcher.utter_message(get_response(self.responses, self.Responses.debug_error).format(str(r.status_code), str(r.headers), str(r.content)))
		else:
			dispatcher.utter_message(get_response(self.responses, self.Responses.error_unknown).format(str(r.content)))
			# DEBUG:
			# dispatcher.utter_message(get_response(self.responses, self.Responses.debug_error).format(str(r.status_code), str(r.headers), str(r.content)))

		return [SlotSet("recommendations", response)]


class ActionAdditionalLearningRecommendation(Action):
	class Responses(ResponseEnum):
		no_more_recommendations = auto()
		additional_recommendations = auto()
		"""
		text additional_recommendations has 1 parameter:
        * parameter {0}: total number (int) of additional (not yet displayed) course recommendations
		"""
		additional_recommendations_single = auto()
		"""
		text additional_recommendations_single has 1 parameter:
        * parameter {0}: total number (int) of additional (not yet displayed) course recommendations
		"""
		additional_course_item = auto()
		"""
		text additional_course_item has 2 parameters:
        * parameter {0}: the title of the course
        * parameter {1}: the URL-parameter /-ID for the course
		"""
		additional_course_item_without_code = auto()
		"""
		text additional_course_item_without has 2 parameters:
        * parameter {0}: the title of the course
        * parameter {1}: URL-encoded string for the title of the course
		"""
		additional_recommendations_more_single = auto()
		"""
		text additional_recommendations_more_single has 1 parameter:
        * parameter {0}: number (int) of found, additional course recommendations (that are not shown yet)
		"""
		additional_recommendations_more_multiple = auto()
		"""
		text additional_recommendations_more_multiple has 1 parameter:
        * parameter {0}: number (int) of found, additional course recommendations (that are not shown yet)
		"""

	responses: Dict[str, str]

	def __init__(self):
		self.responses = get_response_texts(self.name(), ActionResponsesFiles.actions_recommender)
		assert_responses_exist(self.responses, self.Responses)

	def name(self) -> Text:
		return "action_additional_learning_recommendation"

	def run(self, dispatcher: CollectingDispatcher,
			tracker: Tracker,
			domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

		recommendations = tracker.get_slot("recommendations")
		if not recommendations or len(recommendations) <= 3:
			dispatcher.utter_message(get_response(self.responses, self.Responses.no_more_recommendations))
		else:
			recommendations = recommendations[3:]
			size = len(recommendations)
			limit = min(size, 3)
			dispatcher.utter_message(get_response(self.responses, self.Responses.additional_recommendations_single).format(size)) if size == 1 else dispatcher.utter_message(get_response(self.responses, self.Responses.additional_recommendations).format(size))
			course_label = get_response(self.responses, self.Responses.additional_course_item)
			course_label_without_code = get_response(self.responses, self.Responses.additional_course_item_without_code)
			# DISABLED [russa] for consistency, do not use buttons, but normal (link) utterances
			#          TODO maybe change to buttons again, when we allow selecting a course for enrolling
			# button_group = []
			for course in recommendations[0:limit]:
				title = course['name']
				url_param = course['course_code']
				# NOTE [russa] course_code is sometimes empty ...
				# WORKAROUND: if course_code is not available, create link for searching by course title
				if url_param:
					message = course_label.format(title, url_param)
				else:
					message = course_label_without_code.format(title, parse.quote_plus(title))
				# DISABLED [russa] for consistency, do not use buttons, but normal (link) utterances:
				# # NOTE [russa]: disabled setting a payload with the course-title, since there is no real
				# #                interaction, if payload were to be triggered here
				# btn_payload = ''  # '{0}'.format(title)  # TODO enable if/when enrolling in courses is implemented
				# button_group.append({"title": message, "payload": btn_payload})
				dispatcher.utter_message(message)

			# DISABLED [russa] for consistency, do not use buttons, but normal (link) utterances:
			# dispatcher.utter_message(text=" ", buttons=button_group)  # NOTE [russa] non-empty message as WORKAROUND for BUG in socketio-adapter (rasa v3.0-v3.2)

			if limit < size:
				rest = size - limit
				msg_type = self.Responses.additional_recommendations_more_single if rest == 1 else self.Responses.additional_recommendations_more_multiple
				dispatcher.utter_message(get_response(self.responses, msg_type).format(rest))

		return [SlotSet("recommendations", recommendations)]

###################################
# FORMS & SLOTS
###################################

class ActionDeleteSlotValue(Action):
	def name(self):
		return 'action_delete_slot_value'

	def run(self, dispatcher: CollectingDispatcher,
			tracker: Tracker,
			domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

		# check intent then delete slot	value
		intent = str(tracker.get_intent_of_latest_message())
		# print(f"{intent}")  # DEBUG to do: delete - checking function
		if  intent == 'change_language_slot': return [SlotSet("language", None)]
		elif  intent == 'change_topic_slot': return [SlotSet("topic", None)]
		elif  intent == 'change_level_slot': return [SlotSet("level", None)]
		elif  intent == 'change_max_duration_slot': return [SlotSet("max_duration", None)]
		elif  intent == 'change_certificate_slot': return [SlotSet("certificate", None)]
		elif  intent == 'start_recommender_form': return [SlotSet("language", None), SlotSet("topic", None), SlotSet("level", None), SlotSet("max_duration", None), SlotSet("certificate", None)]
		else:  return []


class ActionAskLanguage(Action):
	class Responses(ResponseEnum):
		confirm_and_show_change_language = auto()
		ask_select_language = auto()
		language_option_german = auto()
		language_option_english = auto()
		language_option_any = auto()

	responses: Dict[str, str]

	def __init__(self):
		self.responses = get_response_texts(self.name(), ActionResponsesFiles.actions_recommender)
		assert_responses_exist(self.responses, self.Responses)

	def name(self):
		return 'action_ask_language'

	def run(self, dispatcher: CollectingDispatcher,
			tracker: Tracker,
			domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

		buttons = [
			{'title': get_response(self.responses, self.Responses.language_option_german), 'payload': '/inform{"language":"Deutsch"}'},
			{'title': get_response(self.responses, self.Responses.language_option_english), 'payload': '/inform{"language":"Englisch"}'},
			{'title': get_response(self.responses, self.Responses.language_option_any), 'payload': '/undecided'}]

		# check if slot value should get changed
		intent = str(tracker.get_intent_of_latest_message())
		if intent == 'change_language_slot':
			text = get_response(self.responses, self.Responses.confirm_and_show_change_language)
		# default question
		else:
			text = get_response(self.responses, self.Responses.ask_select_language)

		dispatcher.utter_message(text=text, buttons=buttons)
		return []


class ActionAskTopic(Action):
	class Responses(ResponseEnum):
		confirm_and_show_change_topic = auto()
		ask_select_topic = auto()
		topic_option_introduction_ai = auto()
		topic_option_specialized_ai = auto()
		topic_option_professions_and_ai = auto()
		topic_option_society_and_ai = auto()
		topic_option_data_science = auto()
		topic_option_machine_learning = auto()
		topic_option_any = auto()

	responses: Dict[str, str]

	def __init__(self):
		self.responses = get_response_texts(self.name(), ActionResponsesFiles.actions_recommender)
		assert_responses_exist(self.responses, self.Responses)

	def name(self):
		return 'action_ask_topic'

	def run(self, dispatcher: CollectingDispatcher,
			tracker: Tracker,
			domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

		buttons = [
			{'title': get_response(self.responses, self.Responses.topic_option_introduction_ai), 'payload': '/inform{"topic":"ki-einführung"}'},
			{'title': get_response(self.responses, self.Responses.topic_option_specialized_ai), 'payload': '/inform{"topic":"ki-vertiefung"}'},
			{'title': get_response(self.responses, self.Responses.topic_option_professions_and_ai), 'payload': '/inform{"topic":"ki-berufsfelder"}'},
			{'title': get_response(self.responses, self.Responses.topic_option_society_and_ai), 'payload': '/inform{"topic":"ki-gesellschaft"}'},
			{'title': get_response(self.responses, self.Responses.topic_option_data_science), 'payload': '/inform{"topic":"Data Science"}'},
			{'title': get_response(self.responses, self.Responses.topic_option_machine_learning), 'payload': '/inform{"topic":"Maschinelles Lernen"}'},
			{'title': get_response(self.responses, self.Responses.topic_option_any), 'payload': '/undecided'}]

		intent = str(tracker.get_intent_of_latest_message())
		if intent == 'change_topic_slot':
			text = get_response(self.responses, self.Responses.confirm_and_show_change_topic)
		else:
			text = get_response(self.responses, self.Responses.ask_select_topic)

		dispatcher.utter_message(text=text, buttons=buttons)
		return []


class ActionAskLevel(Action):
	class Responses(ResponseEnum):
		confirm_and_show_change_level = auto()
		ask_select_level = auto()
		level_option_beginner = auto()
		level_option_advanced = auto()
		level_option_expert = auto()

	responses: Dict[str, str]

	def __init__(self):
		self.responses = get_response_texts(self.name(), ActionResponsesFiles.actions_recommender)
		assert_responses_exist(self.responses, self.Responses)

	def name(self):
		return 'action_ask_level'

	def run(self, dispatcher: CollectingDispatcher,
			tracker: Tracker,
			domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

		buttons = [
			{'title': get_response(self.responses, self.Responses.level_option_beginner), 'payload': '/inform{"level":"Anfänger"}'},
			{'title': get_response(self.responses, self.Responses.level_option_advanced), 'payload': '/inform{"level":"Fortgeschritten"}'},
			{'title': get_response(self.responses, self.Responses.level_option_expert), 'payload': '/inform{"level":"Experte"}'}]

		intent = str(tracker.get_intent_of_latest_message())
		if intent == 'change_level_slot':
			text = get_response(self.responses, self.Responses.confirm_and_show_change_level)
		else:
			text = get_response(self.responses, self.Responses.ask_select_level)

		dispatcher.utter_message(text=text, buttons=buttons)
		return []


class ActionAskMaxDuration(Action):
	class Responses(ResponseEnum):
		confirm_and_show_change_duration = auto()
		ask_select_duration = auto()
		duration_option_max_10h = auto()
		duration_option_max_50h = auto()
		duration_option_any = auto()

	responses: Dict[str, str]

	def __init__(self):
		self.responses = get_response_texts(self.name(), ActionResponsesFiles.actions_recommender)
		assert_responses_exist(self.responses, self.Responses)

	def name(self):
		return 'action_ask_max_duration'

	def run(self, dispatcher: CollectingDispatcher,
			tracker: Tracker,
			domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

		buttons = [
			{'title': get_response(self.responses, self.Responses.duration_option_max_10h), 'payload': '/inform{"max_duration":"10"}'},
			{'title': get_response(self.responses, self.Responses.duration_option_max_50h), 'payload': '/inform{"max_duration":"50"}'},
			{'title': get_response(self.responses, self.Responses.duration_option_any), 'payload': '/inform{"max_duration":"51"}'}]

		intent = str(tracker.get_intent_of_latest_message())
		if intent == 'change_max_duration_slot':
			text = get_response(self.responses, self.Responses.confirm_and_show_change_duration)
		else:
			text = get_response(self.responses, self.Responses.ask_select_duration)

		dispatcher.utter_message(text=text, buttons=buttons)
		return []


class ActionAskCertificate(Action):
	class Responses(ResponseEnum):
		confirm_and_show_change_certificate = auto()
		ask_select_certificate = auto()
		certificate_option_unqualified = auto()
		certificate_option_qualified = auto()
		certificate_option_any = auto()

	responses: Dict[str, str]

	def __init__(self):
		self.responses = get_response_texts(self.name(), ActionResponsesFiles.actions_recommender)
		assert_responses_exist(self.responses, self.Responses)

	def name(self):
		return 'action_ask_certificate'

	def run(self, dispatcher: CollectingDispatcher,
			tracker: Tracker,
			domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

		buttons = [
			{'title': get_response(self.responses, self.Responses.certificate_option_unqualified), 'payload': '/inform{"certificate":"Teilnahmebescheinigung"}'},
			{'title': get_response(self.responses, self.Responses.certificate_option_qualified), 'payload': '/inform{"certificate":"Leistungsnachweis"}'},
			{'title': get_response(self.responses, self.Responses.certificate_option_any), 'payload': '/undecided'}]

		intent = str(tracker.get_intent_of_latest_message())
		if intent == 'change_certificate_slot':
			text = get_response(self.responses, self.Responses.confirm_and_show_change_certificate)
		else:
			text = get_response(self.responses, self.Responses.ask_select_certificate)

		dispatcher.utter_message(text=text, buttons=buttons)
		return []

###################################
# CONDITIONAL RESPONSES (VIA SLOTS)
################################### 

class ActionCheckRecommenderFormActive(Action):

	def name(self) -> Text:
		return "action_check_recommender_form_active"

	def run(self, dispatcher: CollectingDispatcher,
			tracker: Tracker,
			domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

		active_loop = str(tracker.active_loop.get('name'))

		if active_loop == 'recommender_form':
			return [SlotSet("recommender_form_active", True)]

		else: return [SlotSet("recommender_form_active", False)]

class ActionRecommenderOrSearchTopics(Action):
	class Responses(ResponseEnum):
		recommender_or_search_topics_unspecified = auto()
		recommender_or_search_topics = auto()
		recommender_option = auto()
		search_topics_option = auto()
		search_topics_option_unspecified = auto()

	responses: Dict[str, str]

	def __init__(self):
		self.responses = get_response_texts(self.name(), ActionResponsesFiles.actions_recommender)
		assert_responses_exist(self.responses, self.Responses)

	def name(self):
		return "action_recommender_or_search_topics"

	def run(self, dispatcher, tracker, domain):
		search_topic = tracker.get_slot("search_topic")

		if search_topic == None:
			buttons =[
				{'title': get_response(self.responses, self.Responses.recommender_option), 'payload': '/start_recommender_form'},
				{'title': get_response(self.responses, self.Responses.search_topics_option_unspecified), 'payload': '/search_topics'},
			]
			text = get_response(self.responses, self.Responses.recommender_or_search_topics_unspecified)
		else:
			search_topic = str(search_topic).capitalize()
			buttons = [
				{'title': get_response(self.responses, self.Responses.recommender_option), 'payload': '/start_recommender_form'},
				{'title': get_response(self.responses, self.Responses.search_topics_option).format(search_topic), 'payload': '/search_topics'},
			]
			text = get_response(self.responses, self.Responses.recommender_or_search_topics).format(search_topic)
		
		dispatcher.utter_message(text=text, buttons=buttons)
		return []

###################################
# VALIDATONS
###################################

class ValidateRecommenderForm(FormValidationAction):
	class Responses(ResponseEnum):
		unsupported_language_selection = auto()
		"""
		text unsupported_language_selection has 1 parameter:
        * parameter {0}: the (unsupported) language
		"""

	responses: Dict[str, str]

	def __init__(self):
		self.responses = get_response_texts(self.name(), ActionResponsesFiles.actions_recommender)
		assert_responses_exist(self.responses, self.Responses)

	def name(self) -> Text:
		return "validate_recommender_form"

	@staticmethod
	def language_db() -> List[Text]:
		"""Database of supported languages"""
		return ["deutsch", "englisch", "egal"]

	@staticmethod
	def language_no_support_db() -> List[Text]:
		"""Database of not supported languages"""
		return ["spanisch", "französisch", "robotisch", "russisch", "slowakisch", "katalanisch", "tschechisch", "mandarin", "hindi", "niederländisch", "schwedisch", "holländisch"]

	@staticmethod
	def topic_db() -> List[Text]:
		"""Database of topics"""
		return ['ki-einführung', 'ki-vertiefung', 'ki-berufsfelder', 'ki-gesellschaft', 'data science', 'maschinelles lernen', 'egal']

	@staticmethod
	def certificate_db() -> List[Text]:
		"""Database of certificates"""
		return ["teilnahmebescheinigung", "leistungsnachweis", "egal"]

	@staticmethod
	def max_duration_db() -> List[Text]:
		"""Database of durations"""
		return ["0", "10", "50", "51"]

	@staticmethod
	def level_db() -> List[Text]:
		"""Database of levels"""
		return ["anfänger", "fortgeschritten", "experte"]

	def validate_language(
		self,
		slot_value: Any,
		dispatcher: CollectingDispatcher,
		tracker: Tracker,
		domain: DomainDict,
	) -> Dict[Text, Any]:
		"""Validate language"""

		if slot_value:
			if slot_value.lower() in self.language_db():
				return {"language": slot_value.lower()}
			elif slot_value.lower() in self.language_no_support_db():
				lang = str(slot_value).capitalize()
				# test for variable
				dispatcher.utter_message(text=get_response(self.responses, self.Responses.unsupported_language_selection).format(lang))
				return {"language": None}

		dispatcher.utter_message(response="utter_interjection_languages")
		return {"language": None}

	def validate_topic(
		self,
		slot_value: Any,
		dispatcher: CollectingDispatcher,
		tracker: Tracker,
		domain: DomainDict,
	) -> Dict[Text, Any]:
		"""Validate topic"""

		if slot_value and slot_value.lower() in self.topic_db():
			return {"topic": slot_value.lower()}
		else:
			dispatcher.utter_message(response = "utter_unavailable_topic")
			return {"topic": None}

	def validate_certificate(
		self,
		slot_value: Any,
		dispatcher: CollectingDispatcher,
		tracker: Tracker,
		domain: DomainDict,
	) -> Dict[Text, Any]:
		"""Validate certificate"""

		if slot_value and slot_value.lower() in self.certificate_db():
			return {"certificate": slot_value.lower()}
		else:
			return {"certificate": None}

	def validate_max_duration(
		self,
		slot_value: Any,
		dispatcher: CollectingDispatcher,
		tracker: Tracker,
		domain: DomainDict,
	) -> Dict[Text, Any]:
		"""Validate max_duration"""

		if slot_value and slot_value.lower() in self.max_duration_db():
			return {"max_duration": slot_value.lower()}
		else:
			return {"max_duration": None}

	def validate_level(
		self,
		slot_value: Any,
		dispatcher: CollectingDispatcher,
		tracker: Tracker,
		domain: DomainDict,
	) -> Dict[Text, Any]:
		"""Validate level"""

		if slot_value and slot_value.lower() in self.level_db():
			return {"level": slot_value.lower()}
		else:
			return {"level": None}
		
		
##########################
# CUSTOM FALLBACK
##########################

class ActionFallbackButtons(Action):
	class Responses(ResponseEnum):
		fallback_message = auto()
		fallback_button_start_recommender_form = auto()
		fallback_button_get_courses = auto()
		fallback_button_greet = auto()
		fallback_button_goodbye = auto()
		fallback_button_thank = auto()
		fallback_button_undecided = auto()
		fallback_button_restart = auto()
		fallback_button_stop_form = auto()
		fallback_button_additional_learning_recommendation = auto()
		fallback_button_change_language_slot = auto()
		fallback_button_change_topic_slot = auto()
		fallback_button_change_level_slot = auto()
		fallback_button_change_max_duration_slot = auto()
		fallback_button_change_certificate_slot = auto()
		fallback_button_deny = auto()
		fallback_button_affirm = auto()
		fallback_button_get_achievements = auto()
		fallback_button_help = auto()
		fallback_button_bot_challenge = auto()
		fallback_button_human_handoff = auto()
		fallback_button_search_topics = auto()
		fallback_button_ask_question = auto()

	responses: Dict[str, str]

	def __init__(self):
		self.responses = get_response_texts(self.name(), ActionResponsesFiles.actions_recommender)
		assert_responses_exist(self.responses, self.Responses)

	def name(self):
		return 'action_fallback_buttons'

	def run(self, dispatcher: CollectingDispatcher,
			tracker: Tracker,
			domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
		
        # select the top two intents from the tracker        
        # ignore the first one - nlu fallback
		predicted_intents = tracker.latest_message["intent_ranking"][1:4]
		text = get_response(self.responses, self.Responses.fallback_message)

		# mapping between intents and button text
		intent_mappings = {
			"greet": get_response(self.responses, self.Responses.fallback_button_greet),
			"goodbye": get_response(self.responses, self.Responses.fallback_button_goodbye),
			"thank": get_response(self.responses, self.Responses.fallback_button_thank),
			"undecided": get_response(self.responses, self.Responses.fallback_button_undecided),
			"restart": get_response(self.responses, self.Responses.fallback_button_restart),
			"stop_form": get_response(self.responses, self.Responses.fallback_button_stop_form),
			"additional_learning_recommendation": get_response(self.responses, self.Responses.fallback_button_additional_learning_recommendation),
			"change_language_slot": get_response(self.responses, self.Responses.fallback_button_change_language_slot),
			"change_topic_slot": get_response(self.responses, self.Responses.fallback_button_change_topic_slot),
			"change_level_slot": get_response(self.responses, self.Responses.fallback_button_change_level_slot),
			"change_max_duration_slot": get_response(self.responses, self.Responses.fallback_button_change_max_duration_slot),
			"change_certificate_slot": get_response(self.responses, self.Responses.fallback_button_change_certificate_slot),
			"deny": get_response(self.responses, self.Responses.fallback_button_deny),
			"affirm": get_response(self.responses, self.Responses.fallback_button_affirm),
			"get_achievements": get_response(self.responses, self.Responses.fallback_button_get_achievements),
			"help": get_response(self.responses, self.Responses.fallback_button_help),
			"bot_challenge": get_response(self.responses, self.Responses.fallback_button_bot_challenge),
			"search_topics": get_response(self.responses, self.Responses.fallback_button_search_topics)
			}

		buttons = [	
			{'title': get_response(self.responses, self.Responses.fallback_button_ask_question), 'payload': '/ask_question'},
			{'title': get_response(self.responses, self.Responses.fallback_button_start_recommender_form), 'payload': '/start_recommender_form'},
			{'title': get_response(self.responses, self.Responses.fallback_button_get_courses), 'payload': '/get_courses'},
			{'title': get_response(self.responses, self.Responses.fallback_button_human_handoff), 'payload': '/human_handoff'}]
		
		for intent in predicted_intents:
			if intent['name'] not in intent_mappings:
					continue
			
			button_title = "{}".format(intent_mappings[intent['name']])
			button_payload = "/{}".format(intent['name'])
			buttons.append({"title": button_title, "payload": button_payload})

		dispatcher.utter_message(text=text, buttons=buttons)
		return []