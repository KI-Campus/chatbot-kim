from enum import auto
from typing import Text, Dict, Any, List
from rasa_sdk import Action, Tracker
from rasa_sdk.events import SlotSet, SessionStarted
from sanic.request import Request
from rasa_sdk.executor import CollectingDispatcher

import requests
import json

from .responses import get_response_texts, assert_responses_exist, ResponseEnum, get_response


class CourseSet(Action):
	def name(self):
		return "action_course_set"

	def run(self, dispatcher, tracker, domain):
		currentCourse = tracker.get_slot('current_course_title')
		if currentCourse:
			return [SlotSet('course-set', True)]
		else:
			return [SlotSet('course-set', False)]



class ActionGetCoursesButtons(Action):
	class Responses(ResponseEnum):
		no_courses = auto()
		list_courses = auto()
		course_label = auto()
		"""
		text course_label has 1 parameter:
        * parameter {0}: the title of the course
		"""
		error_401 = auto()

	responses: Dict[str, str]

	def __init__(self):
		self.responses = get_response_texts(self.name())
		assert_responses_exist(self.responses, self.Responses)

	def name(self) -> Text:
		return "action_get_courses_buttons"

	def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
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
				dispatcher.utter_message(get_response(self.responses, self.Responses.no_courses))
				return [SlotSet('courses_available', False)]
			else:
				dispatcher.utter_message(get_response(self.responses, self.Responses.list_courses))
				courseTitle = get_response(self.responses, self.Responses.course_label)
				buttonGroup = []
				for course in response:
					title = course['title']
					buttonGroup.append({"title": courseTitle.format(title), "payload": '/courses{{"Course": "{0}"}}'.format(title)})
				dispatcher.utter_message(buttons = buttonGroup)
				return [SlotSet('all_courses', response), SlotSet('courses_available', True)]
		elif status == 401:  # Status-Code 401 None
			dispatcher.utter_message(get_response(self.responses, self.Responses.error_401))
			return [SlotSet('courses_available', False)]
		else:
			return []


class ActionGetCourses(Action):
	class Responses(ResponseEnum):
		no_courses = auto()
		list_courses = auto()
		course_title = auto()
		"""
		text course_title has 1 parameter:
        * parameter {0}: the title of the course
		"""
		error_401 = auto()

	responses: Dict[str, str]

	def __init__(self):
		self.responses = get_response_texts(self.name())
		assert_responses_exist(self.responses, self.Responses)

	def name(self) -> Text:
		return "action_get_courses"

	def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
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
				dispatcher.utter_message(get_response(self.responses, self.Responses.no_courses))
				return [SlotSet('courses_available', False)]
			else:
				dispatcher.utter_message(get_response(self.responses, self.Responses.list_courses))
				courseTitle = get_response(self.responses, self.Responses.course_title)
				for course in response:
					title = courseTitle.format(course['title'])
					dispatcher.utter_message(title)
				return [SlotSet('all_courses', response), SlotSet('courses_available', True)]
		elif status == 401:  # Status-Code 401 None
			dispatcher.utter_message(get_response(self.responses, self.Responses.error_401))
			return [SlotSet('courses_available', False)]
		else:
			return []


class ActionGetAchievements(Action):
	class Responses(ResponseEnum):
		request_language_code = auto()
		achievement_description = auto()
		"""
		text achievement_description has 1 parameter:
        * parameter {0}: (textual) description of field "description" in data-object for achievement
		"""
		course_not_found = auto()

	responses: Dict[str, str]

	def __init__(self):
		self.responses = get_response_texts(self.name())
		assert_responses_exist(self.responses, self.Responses)

	def name(self) -> Text:
		return "action_get_achievements"

	def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
		course_achieved = False
		currentCourse = []
		courseId = 0
		currentAchievements = []
		current_state = tracker.current_state()
		token = current_state['sender_id']
		currentCourseTitle = tracker.slots['current_course_title']
		allCourses = tracker.slots['all_courses']
		for course in allCourses:
			if currentCourseTitle in course['title']:
				courseId = course['id']
				currentCourse = course
				break
		if courseId != 0:
			req_lang = get_response(self.responses, self.Responses.request_language_code)
			r = requests.get('https://learn.ki-campus.org/bridges/chatbot/my_courses/{0}/achievements'.format(courseId),
			headers={
				"content-type": "application/json",
				"Authorization": 'Bearer {0}'.format(token),
				"Accept-Language": "{0}".format(req_lang)
			})
			status = r.status_code
			if status == 200:
				response = json.loads(r.content)
				currentAchievements = response['certificates']
				for achievement in currentAchievements:
					dispatcher.utter_message(get_response(self.responses, self.Responses.achievement_description).format(achievement['description']))
					if achievement['achieved'] and not course_achieved:
						course_achieved = True
			return [SlotSet('current_course_achieved', course_achieved),
				SlotSet('current_course', currentCourse),
				SlotSet('current_achievements', currentAchievements),
				SlotSet('current_course_title', None)]
		else:
			dispatcher.utter_message(get_response(self.responses, self.Responses.course_not_found))
			return[SlotSet('current_course_achieved', course_achieved), 
			SlotSet('current_course', currentCourse), 
			SlotSet('current_achievements', currentAchievements), 
			SlotSet('current_course_title', None)]


class ActionGetCertificate(Action):
	class Responses(ResponseEnum):
		download_achievement = auto()
		"""
		text download_achievement has 2 parameters:
        * parameter {0}: field "name" in data-object for achievement
        * parameter {1}: field "url" in "download"-field in data-object for achievement, i.e. achievement['download']['url']
		"""
		download_not_available = auto()
		"""
		text download_not_available has 1 parameter:
        * parameter {0}: field "name" in data-object for achievement
		"""

	responses: Dict[str, str]

	def __init__(self):
		self.responses = get_response_texts(self.name())
		assert_responses_exist(self.responses, self.Responses)

	def name(self) -> Text:
		return "action_download_certificate"

	def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
		currentAchievements = tracker.slots['current_achievements']
		for achievement in currentAchievements:
			if achievement['achieved']:
				if achievement['download']['available']:
					dispatcher.utter_message(get_response(self.responses, self.Responses.download_achievement).format(achievement['name'], achievement['download']['url']))
				else:
					dispatcher.utter_message(get_response(self.responses, self.Responses.download_not_available).format(achievement['name']))
		return []

class ActionSearchTopic(Action):
	class Responses(ResponseEnum):
		topicpage_present = auto()
		"""
		text topicpage_present has 2 parameter:
        * parameter {0}: (textual) search topic
								* parameter {0}: (textual) link to search topic
		"""
		topicpage_not_present = auto()
		"""
		text topicpage_present has 1 parameter:
        * parameter {0}: (textual) search topic
		"""

	responses: Dict[str, str]

	def __init__(self):
		self.responses = get_response_texts(self.name())
		assert_responses_exist(self.responses, self.Responses)
	def name(self) -> Text:
		return "action_search_topic"
	
	def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
		searchTopic = tracker.latest_message['entities'][0]['value']

		if searchTopic.lower() == 'medizin':
			dispatcher.utter_message(get_response(self.responses, self.Responses.topicpage_present).format("Medizin", "https://ki-campus.org/themen/medizin"))
		elif searchTopic.lower() == 'schule':
			dispatcher.utter_message(get_response(self.responses, self.Responses.topicpage_present).format("Schule", "https://ki-campus.org/themen/schule"))
		elif searchTopic.lower() == 'daten':
			dispatcher.utter_message(get_response(self.responses, self.Responses.topicpage_present).format("Daten", "https://ki-campus.org/themen/daten"))
		elif searchTopic.lower() == 'machine learning':
			dispatcher.utter_message(get_response(self.responses, self.Responses.topicpage_present).format("Machine Learning", "https://ki-campus.org/themen/machine-learning"))
		elif searchTopic.lower() == 'entrepreneurship':
			dispatcher.utter_message(get_response(self.responses, self.Responses.topicpage_present).format("Entrepreneurship", "https://ki-campus.org/themen/entrepreneurship"))
		else:
			dispatcher.utter_message(get_response(self.responses, self.Responses.topicpage_not_present).format(searchTopic))
		return[]
