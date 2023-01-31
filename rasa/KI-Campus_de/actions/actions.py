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
		r = requests.get('https://lernen.cloud/bridges/chatbot/my_courses',
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
		r = requests.get('https://lernen.cloud/bridges/chatbot/my_courses',
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
			r = requests.get('https://lernen.cloud/bridges/chatbot/my_courses/{0}/achievements'.format(courseId), 
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


def extract_courses(response):
	# Merge all match types (potentially duplicated courses)
	potential_duplicated_courses = [
		course
		for respones in response.values()
		for course in respones
	]

	# Deduplicate dicts in a list
	matches = [
		dict(t) 
		for t in 
			{tuple(e.items()) for e in potential_duplicated_courses}
	]

	return matches


class ActionAnswerExternalSearch(Action):
	def name(self) -> Text:
		return "action_answer_external_search"
	
	def run(self, dispatcher, tracker, domain):
		search_topic = tracker.get_slot("given_search_topic")
		if not search_topic:
			dispatcher.utter_message('Ich hab leider nicht verstanden nach welchem Thema du suchst.')
			return []
		else:
			r = requests.get(f'http://82.140.0.82/api/external_search?keyword={search_topic}')
			status = r.status_code

			course_in_other_language = False
			if status == 200:
				response = json.loads(r.content)
		
				matches = extract_courses(response)
				if matches == []:
					dispatcher.utter_message(f'Ich konnte leider keine Kurse zum Thema {search_topic} finden. Versuche es doch mit einem anderen Begriff.')
				else:
					first_found_match = False
					for match in matches:
						if match['language'] == 'de':
							if not first_found_match:
								dispatcher.utter_message(f'Ich habe folgende Kurse zum Thema {search_topic} gefunden:')
								first_found_match = True
							dispatcher.utter_message(f'- {match["title"]}: {match["url"]}')
						else:
							course_in_other_language = True
			else:
				dispatcher.utter_message(f'Leider ist ein Fehler bei der Suche aufgetreten.')

			if course_in_other_language:
				dispatcher.utter_message(response = "utter_ask_courses_other_language")
				return []

			return [SlotSet('given_search_topic', None)]
	

class ActionAnswerExternalSearchOtherLanguages(Action):
	def name(self) -> Text:
		return "action_answer_external_search_other_languages"

	def run(self, dispatcher, tracker, domain):
		search_topic = tracker.get_slot("given_search_topic")

		r = requests.get(f'http://82.140.0.82/api/external_search?keyword={search_topic}')
		status = r.status_code
		if status == 200:
			response = json.loads(r.content)
			matches = extract_courses(response)
			dispatcher.utter_message(f'Ich habe folgende Kurse zum Thema {search_topic} in anderen Sprachen gefunden:')
			for match in matches:
				if match['language'] != 'de':
					dispatcher.utter_message(f'- {match["title"]}: {match["url"]}')
		
		return [SlotSet('given_search_topic', None)]


class ActionDeleteGivenSearchTopic(Action):
	def name(self) -> Text:
		return "action_delete_given_search_topic"
	
	def run(self, dispatcher, tracker, domain):
		return [SlotSet('given_search_topic', None)]
		

class ActionAnswerInternalSearch(Action):
	def name(self) -> Text:
		return "action_answer_internal_search"
	
	def run(self, dispatcher, tracker, domain, second_run = False):
		if second_run:
			content_type = 'All'
		else:
			content_type = tracker.get_slot('given_search_content_type')
		search_topic = tracker.get_slot('given_search_topic')

		got_response = False

		content_type_mapping = {
		"Video": "video",
		"Text": "rich_text",
		"Quiz": "quiz",
		"Übung": "lti_exercise"
		}

		inv_content_type_mapping = {v: k for k, v in content_type_mapping.items()}

		# Get courses where the user is enrolled
		current_state = tracker.current_state()
		token = current_state['sender_id']
		r_courses = requests.get('https://lernen.cloud/bridges/chatbot/my_courses',
		headers={
			"content-type": "application/json",
			"Authorization": 'Bearer {0}'.format(token)
		})

		status_courses = r_courses.status_code

		if status_courses == 200:
			response = json.loads(r_courses.content)
			# TODO: Check what is returned when not enrolled in a course 200 and empty list or 401
			if len(response) < 1:
				dispatcher.utter_message('Du bist derzeit in keinem Kurs eingeschrieben. Hier sind passende Kurse zu dem Thema:')
				ActionAnswerExternalSearch.run(self, dispatcher, tracker, domain)
				return [SlotSet('given_search_content_type', None), SlotSet('given_search_topic', None)]
			else:
				for course in response:
					# If the content type is given use it in the API request
					if content_type not in content_type_mapping.keys():
						content_type = 'All'
						req = f'http://82.140.0.82/api/keyword_search?keyword={search_topic}&course={course["course_code"]}'
					else:
						req = f'http://82.140.0.82/api/keyword_search?keyword={search_topic}&content_type={content_type_mapping[content_type]}&course={course["course_code"]}'

					r = requests.get(req)
					status = r.status_code
					if status == 200:
						response = json.loads(r.content)

						if(response != {}):
							dispatcher.utter_message(f'Ich habe folgende Inhalte zu {search_topic} in dem Kurs {course["title"]} gefunden:')
							for current_content_type in response.keys():
								if(content_type == "All"):
									dispatcher.utter_message(f'Inhalte vom Typ {inv_content_type_mapping[current_content_type]}:')
								for item in response[current_content_type]:
									dispatcher.utter_message(f'- {item["title"]}: http://lernen.cloud{item["href"]}')
							got_response = True			
					
					# If status code for get internal items is != 200
					else:
						dispatcher.utter_message('Leider ist ein Fehler aufgetreten. Probiere es später noch ein Mal.')
						return [SlotSet('given_search_content_type', None), SlotSet('given_search_topic', None)]
				
				# Nothing with the search topic was found in none of the courses where the user is enrolled
				if(not got_response):
					if content_type != 'All':
						second_run = True
						dispatcher.utter_message(f'Innerhalb deiner Kurse konnte ich nichts vom Typ {content_type} zum Thema {search_topic} finden.')
						ActionAnswerInternalSearch.run(self, dispatcher, tracker, domain, second_run)
					else:
						dispatcher.utter_message(f'Innerhalb deiner Kurse konnte ich nichts finden. Ich suche jetzt nach anderen Kursen zum Thema {search_topic}.')
						ActionAnswerExternalSearch.run(self, dispatcher, tracker, domain)
				
				return [SlotSet('given_search_content_type', None), SlotSet('given_search_topic', None)]

		# Got an error code while requesting the courses where a user is enrolled
		else:
			dispatcher.utter_message('Leider ist ein Fehler aufgetreten. Probiere es später noch ein Mal.')
			return [SlotSet('given_search_content_type', None), SlotSet('given_search_topic', None)]
			
		
class ActionDefaultFallback(Action):
	def name(self) -> Text:
		return "action_default_fallback"

	def run(self, dispatcher, tracker, domain):
		top_intents = []

		if "intent_ranking"  in tracker.latest_message.keys():
			for i in range(min(len(tracker.latest_message['intent_ranking']), 3)):
				top_intents.append(tracker.latest_message['intent_ranking'][i]['name'])	
		elif "intent" in tracker.latest_message.keys():
			top_intents.append(tracker.latest_message['intent']['name'])

		if ('search_internal' in top_intents) or ('search_external' in top_intents):
			dispatcher.utter_message(response = "utter_ask_internal_or_external_search")
			return []
		else:
			dispatcher.utter_message(response = "utter_default")
			return []
