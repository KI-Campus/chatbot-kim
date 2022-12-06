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
			if len(response) < 1:
				dispatcher.utter_message('Du bist derzeit in keinem Kurs eingeschrieben.')
				return [SlotSet('courses_available', False)]
			else:
				dispatcher.utter_message('Du bist derzeit in diesen Kursen eingeschrieben:')
				buttonGroup = []
				for course in response:
					title = course['title']
					buttonGroup.append({"title": title, "payload": '/inform{{"Course": "{0}"}}'.format(title)})
				dispatcher.utter_message(buttons = buttonGroup)
				return [SlotSet('all_courses', response), SlotSet('courses_available', True)]
		elif status == 401: # Status-Code 401 None
			dispatcher.utter_message('Du bist derzeit in keinem Kurs eingeschrieben.')
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
				dispatcher.utter_message('Du bist derzeit in keinem Kursen eingeschrieben.')
				return [SlotSet('courses_available', False)]
			else:
				dispatcher.utter_message('Du bist derzeit in diesen Kursen eingeschrieben:')
				for course in response:
					title = course['title']
					dispatcher.utter_message(title)
				return [SlotSet('all_courses', response), SlotSet('courses_available', True)]
		elif status == 401: # Status-Code 401 None
			dispatcher.utter_message('Du bist derzeit in keinem Kursen eingeschrieben.')
			return [SlotSet('courses_available', False)]
		else:
			return []

class ActionGetAchievements(Action):
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
			r = requests.get('https://learn.ki-campus.org/bridges/chatbot/my_courses/{0}/achievements'.format(courseId), 
			headers={
				"content-type": "application/json",
				"Authorization": 'Bearer {0}'.format(token), 
				"Accept-Language": "de"
			})
			status = r.status_code
			if status == 200:
				response = json.loads(r.content)
				currentAchievements = response['certificates']
				for achievement in currentAchievements:
					dispatcher.utter_message('{0}'.format(achievement['description']))
					if achievement['achieved'] and not course_achieved:
						course_achieved = True
			return[SlotSet('current_course_achieved', course_achieved), 
			SlotSet('current_course', currentCourse), 
			SlotSet('current_achievements', currentAchievements),
			SlotSet('current_course_title', None)]
		else:
			dispatcher.utter_message('Es tut mir sehr leid! Ich konnte den Kurs, den du suchst, nicht finden. Bitte versuche es erneut, in dem du mir den Kurstitel nennst.')
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
					dispatcher.utter_message('Hier kannst du {0}: {1} herunterladen!'.format(achievement['name'], achievement['download']['url']))
				else:
					dispatcher.utter_message('Es tut mir sehr leid! Das {0} ist nicht mehr verfügbar und kann leider nicht mehr heruntergeladen werden!'.format(achievement['name']))
		return []


class ActionAnswerExternalSearch(Action):
	def name(self) -> Text:
		return "action_answer_external_search"
	
	def run(self, dispatcher, tracker, domain):
		dispatcher.utter_message('Danke für deine externe Suchanfrage zum Thema {0}!'.format(tracker.get_slot('given_search_topic_external')))
		return []


class ActionAnswerInternalSearch(Action):
	def name(self) -> Text:
		return "action_answer_internal_search"
	
	def run(self, dispatcher, tracker, domain):
		content_type = tracker.get_slot('given_search_content_type')
		search_topic = tracker.get_slot('given_search_topic_internal')

		dispatcher.utter_message(f'Danke für deine interne Suchanfrage nach einem {content_type} zum Thema {search_topic}!')
		return [SlotSet('given_search_content_type', None), SlotSet('given_search_topic_internal', None)]

class ActionDefaultFallback(Action):

    def name(self) -> Text:
        return "action_default_fallback"

    def run(self, dispatcher, tracker, domain):

        top_intents = []
		
        if "intent_ranking"  in tracker.latest_message.keys():
            for i in range(min(len(tracker.latest_message['intent_ranking']), 3)):
                top_intents.append(tracker.latest_message['intent_ranking'][i]['name'])	
        else:
            top_intents.append(tracker.latest_message['intent']['name'])
			
        print(tracker.latest_message)

        if ('search_internal' in top_intents) and ('search_external' in top_intents):
            dispatcher.utter_message(f'Willst du in diesem Kurs suchen, oder einen neuen Kurs finden? Top_intents: {top_intents}')
            return [SlotSet('run_default', None)]
        else:
            dispatcher.utter_message(f'Default Fallback. top_intents: {top_intents}')
            return [SlotSet('run_default', True)]