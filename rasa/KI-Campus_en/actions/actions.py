from typing import Text, Dict, Any, List
from rasa_sdk import Action, Tracker
from rasa_sdk.events import SlotSet, SessionStarted
from sanic.request import Request
from rasa_sdk.executor import CollectingDispatcher

import requests
import json

class CourseSet(Action):
	def name(self):
		return "action_course_set"

	def run(self, dispatcher, tracker, domain):
		currentCourse = tracker.get_slot('current_course_title')
		if currentCourse:
			return [SlotSet('course-set', True)]
		else:
			return [SlotSet('course-set', False)]

class ActionGetCourses(Action):
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
			print(response)
			if len(response) < 1:
				dispatcher.utter_message('You are currently not enrolled in any courses.')
				return [SlotSet('courses_available', False)]
			else:
				dispatcher.utter_message('You are currently enrolled in these courses:')
				buttonGroup = []
				for course in response:
					title = course['title']
					buttonGroup.append({"title": title, "payload": '/inform{{"Course": "{0}"}}'.format(title)})
				dispatcher.utter_message(buttons = buttonGroup)
				return [SlotSet('all_courses', response), SlotSet('courses_available', True)]
		elif status == 401: # Status-Code 401 None
			dispatcher.utter_message('You are currently not enrolled in any courses.')
			return [SlotSet('courses_available', False)]
		else:
			return []

class ActionGetCourses(Action):
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
				dispatcher.utter_message('You are currently not enrolled in any courses.')
				return [SlotSet('courses_available', False)]
			else:
				dispatcher.utter_message('You are currently enrolled in these courses:')
				for course in response:
					title = course['title']
					dispatcher.utter_message(title)
				return [SlotSet('all_courses', response), SlotSet('courses_available', True)]
		elif status == 401: # Status-Code 401 None
			dispatcher.utter_message('You are currently not enrolled in any courses.')
			return [SlotSet('courses_available', False)]
		else:
			return []

class ActionGetAchievements(Action):
	def name(self) -> Text:
		return "action_get_achievements"

	def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
		print("action get achievements")
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
			r = requests.get('https://learn.ki-campus.org/bridges/chatbot/my_courses/{0}/achievements'.format(courseId), 
			headers={
				"content-type": "application/json",
				"Authorization": 'Bearer {0}'.format(token), 
				"Accept-Language": "en"
			})
			status = r.status_code
			if status == 200:
				response = json.loads(r.content)
				currentAchievements = response['certificates']
				for achievement in currentAchievements:
					dispatcher.utter_message('{0}'.format(achievement['description']))
					if achievement['achieved'] and not course_achieved:
						course_achieved = True
			return[SlotSet('current_course_achieved', course_achieved), SlotSet('current_course', currentCourse), SlotSet('current_achievements', currentAchievements)]
		else:
			dispatcher.utter_message('I am very sorry! I could not find the course you are looking for. Please try again by telling me the course title.')
			return[SlotSet('current_course_achieved', course_achieved), 
			SlotSet('current_course', currentCourse), 
			SlotSet('current_achievements', currentAchievements),
			SlotSet('current_course_title', None)]

class ActionGetCertificate(Action):
	def name(self) -> Text:
		return "action_download_certificate"

	def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
		currentAchievements = tracker.slots['current_achievements']
		for achievement in currentAchievements:
			if achievement['achieved']:
				if achievement['download']['available']:
					dispatcher.utter_message('You can download your {0} here: {1}!'.format(achievement['name'], achievement['download']['url']))
				else:
					dispatcher.utter_message('I am very sorry! The {0} is no longer available and unfortunately can no longer be downloaded!'.format(achievement['name']))
		return []
