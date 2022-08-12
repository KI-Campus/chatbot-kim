from typing import Text, Dict, Any, List
from rasa_sdk import Action, Tracker
from rasa_sdk.events import SlotSet, SessionStarted
from sanic.request import Request
from rasa_sdk.executor import CollectingDispatcher

import requests
import json

# dfki test
import random

from rasa_sdk import FormValidationAction
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import EventType, Restarted, AllSlotsReset
from rasa_sdk.types import DomainDict
####

class CourseSet(Action):
	def name(self):
		return "action_course_set"

	def run(self, dispatcher, tracker, domain):
		currentCourse = tracker.get_slot('current_course_title')
		if currentCourse:
			return [SlotSet('course-set', True)]
		else:
			return [SlotSet('course-set', False)]

class PrintAllSlots(Action):
	def name(self):
		return "action_all_slots"

	def run(self, dispatcher, tracker, domain):
		currentCourse = tracker.get_slot('current_course_title')
		return []

class SetCurrentCourse(Action):
	def name(self):
		return "action_set_current_course"

	def run(self, dispatcher, tracker, domain):
		currentCourse = tracker.latest_message['text']
		return [SlotSet('current_course_title', currentCourse)]


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
				dispatcher.utter_message('Du bist derzeit in keinem Kursen eingeschrieben.')
				return [SlotSet('courses_available', False)]
			else:
				dispatcher.utter_message('Du bist derzeit in diesen Kursen eingeschrieben:')
				buttonGroup = []
				for course in response:
					title = course['title']
					buttonGroup.append({"title": title, "payload": '{0}'.format(title)})
				dispatcher.utter_message(buttons = buttonGroup)
				return [SlotSet('all_courses', response), SlotSet('courses_available', True)]
		elif status == 401: # Status-Code 401 None
			dispatcher.utter_message('Du bist derzeit in keinem Kursen eingeschrieben.')
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
			return[SlotSet('current_course_achieved', course_achieved), SlotSet('current_course', currentCourse), SlotSet('current_achievements', currentAchievements)]
		else:
			dispatcher.utter_message('Es tut mir sehr leid! Ich konnte den Kurs, den du suchst, nicht finden. Bitte versuche es erneut, indem du mir den Kurstitel nennen.')
			return[SlotSet('current_course_achieved', course_achieved), SlotSet('current_course', currentCourse), SlotSet('current_achievements', currentAchievements)]


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

############# DFKI ###############

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

        user_login = random.choice([True, False]) # to do: implement login check

        return [SlotSet("user_login", user_login)]

class ActionFetchProfile(Action):
    
    def name(self) -> Text:
        return "action_fetch_profile"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
            
        user_id = "22218451-41f0-23dd-c50f-cdd8096610c1"        
		# if re.search(".*", user_id): SlotSet("user_id", user_id) # create regex
        # else: return [SlotSet("user_id", None), dispatcher.utter_message("User ist nicht eingeloggt.")]
        enrollments = ["Einführung in die KI", "Mensch-Maschine-Interaktion"]
        course_visits = ["Big Data Analytics"]
        search_terms = ["KI", "Machine Learning"]
        #to do: implement profile checkup

        return [SlotSet("user_id", user_id), SlotSet("enrollments", enrollments), SlotSet("course_visits", course_visits), SlotSet("search_terms", search_terms)]

######################################################################################
# RECOMMENDER
######################################################################################

class ActionGetLearningRecommendation(Action):

    def name(self) -> Text:
        return "action_get_learning_recommendation"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        language = str(tracker.get_slot("language"))
        topic = str(tracker.get_slot("topic"))
        level = str(tracker.get_slot("level"))
        max_duration = int(tracker.get_slot("max_duration")) 
        certificate = str(tracker.get_slot("certificate"))
        enrollments = tracker.get_slot("enrollments")
        course_visits = tracker.get_slot("course_visits")
        search_terms = tracker.get_slot("search_terms")
        
		# to do: implement recommender
		# to do: maybe option 2 implement after delete slot value
        dispatcher.utter_message(text = "Also, ich empfehle dir folgende Lernangebote: \n\nLernangebot Beispiel")
        return []

class ActionAdditionalLearningRecommendation(Action):

    def name(self) -> Text:
        return "action_additional_learning_recommendation"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        # to do: implement search for more recommendations
        dispatcher.utter_message(text = "Also, ich empfehle dir folgende Lernangebote: \n\nLernangebot Beispiel")
        return []

##########################################################################################
# FORMS & SLOTS
##########################################################################################

class ActionDeleteSlotValue(Action):
    def name(self):
        return 'action_delete_slot_value'

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

		# check intent then delete slot	value
        intent = str(tracker.get_intent_of_latest_message())
        print(f"{intent}") # to do: delete - checking function
        if  intent == 'change_language_slot': return [SlotSet("language", None)]
        elif  intent == 'change_topic_slot': return [SlotSet("topic", None)]
        elif  intent == 'change_level_slot': return [SlotSet("level", None)]
        elif  intent == 'change_max_duration_slot': return [SlotSet("max_duration", None)]
        elif  intent == 'change_certificate_slot': return [SlotSet("certificate", None)]
        else:  return [dispatcher.utter_message('Kein Slot Value gelöscht')]

class ActionAskLanguage(Action):
    def name(self):
        return 'action_ask_language'

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
		# check if slot value should get changed
        intent = str(tracker.get_intent_of_latest_message())
        if intent == 'change_language_slot':
            text = "Wie ich verstanden habe, möchtest du die Sprache für deine Kursempfehlungen ändern. Wähle eine der Sprachoptionen aus!"
            buttons = [{'title': 'Deutsch', 'payload': '/inform_coursesearch{"language":"Deutsch"}'},
    			{'title': 'Englisch', 'payload': '/inform_coursesearch{"language":"Englisch"}'},
				{'title': 'Beide Sprachen', 'payload': '/undecided'}]
            dispatcher.utter_message(text = text, buttons = buttons)
		# default question
        else:
            text = "Soll der Kurs auf Deutsch oder auf Englisch sein?"
            buttons = [{'title': 'Deutsch', 'payload': '/inform_coursesearch{"language":"Deutsch"}'},
    			{'title': 'Englisch', 'payload': '/inform_coursesearch{"language":"Englisch"}'},
				{'title': 'Beide Sprachen', 'payload': '/undecided'}]
            dispatcher.utter_message(text = text, buttons = buttons)
        return []

class ActionAskTopic(Action):
    def name(self):
        return 'action_ask_topic'

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        intent = str(tracker.get_intent_of_latest_message())
        if intent == 'change_topic_slot':
            text = "Du möchtest also das Thema für deine Kursempfehlungen ändern. Hier ist eine Auswahl unserer Themen:"
            buttons = [{'title': 'Einführung in die KI', 'payload': '/inform_coursesearch{"topic":"ki-einführung"}'},
    		    {'title': 'Vertiefung einzelner Themenfelder der KI', 'payload': '/inform_coursesearch{"topic":"ki-vertiefung"}'},
			    {'title': 'KI in Berufsfeldern', 'payload': '/inform_coursesearch{"topic":"ki-berufsfelder"}'},
			    {'title': 'KI und Gesellschaft', 'payload': '/inform_coursesearch{"topic":"ki-gesellschaft"}'},
			    {'title': 'Data Science', 'payload': '/inform_coursesearch{"topic":"Data Science"}'},
			    {'title': 'Maschinelles Lernen', 'payload': '/inform_coursesearch{"topic":"Maschinelles Lernen"}'},
			    {'title': 'egal', 'payload': '/undecided'}]
            dispatcher.utter_message(text = text, buttons = buttons)
        else:
            text = "Worum soll es in deinem Wunsschkurs gehen? Wähle eins der folgenden Themenfelder!"
            buttons = [{'title': 'Einführung in die KI', 'payload': '/inform_coursesearch{"topic":"ki-einführung"}'},
    		    {'title': 'Vertiefung einzelner Themenfelder der KI', 'payload': '/inform_coursesearch{"topic":"ki-vertiefung"}'},
			    {'title': 'KI in Berufsfeldern', 'payload': '/inform_coursesearch{"topic":"ki-berufsfelder"}'},
			    {'title': 'KI und Gesellschaft', 'payload': '/inform_coursesearch{"topic":"ki-gesellschaft"}'},
			    {'title': 'Data Science', 'payload': '/inform_coursesearch{"topic":"Data Science"}'},
			    {'title': 'Maschinelles Lernen', 'payload': '/inform_coursesearch{"topic":"Maschinelles Lernen"}'},
			    {'title': 'egal', 'payload': '/undecided'}]
            dispatcher.utter_message(text = text, buttons = buttons)
        return []

class ActionAskLevel(Action):
    def name(self):
        return 'action_ask_level'

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        intent = str(tracker.get_intent_of_latest_message())
        if intent == 'change_level_slot':
            text = "Du möchtest also das Level von deinem Wunschkurs ändern. Die Kurse auf dem KI-Campus haben die folgenden Level zur Auswahl:"
            buttons = [{'title': 'Anfänger*in', 'payload': '/inform_coursesearch{"level":"Anfänger"}'},
    		{'title': 'Fortgeschrittene*r', 'payload': '/inform_coursesearch{"level":"Fortgeschritten"}'},
			{'title': 'Experte', 'payload': '/inform_coursesearch/inform_coursesearch{"level":"Experte"}'}]
        
            dispatcher.utter_message(text = text, buttons = buttons)
        else:
            text = "Wie schätzt du deine Vorkenntnisse im Bereich KI ein?"
            buttons = [{'title': 'Anfänger*in', 'payload': '/inform_coursesearch{"level":"Anfänger"}'},
    		{'title': 'Fortgeschrittene*r', 'payload': '/inform_coursesearch{"level":"Fortgeschritten"}'},
			{'title': 'Experte', 'payload': '/inform_coursesearch/inform_coursesearch{"level":"Experte"}'}]
        
            dispatcher.utter_message(text = text, buttons = buttons)
        return []

class ActionAskMaxDuration(Action):
    def name(self):
        return 'action_ask_max_duration'

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        intent = str(tracker.get_intent_of_latest_message())
        if intent == 'change_max_duration_slot':
            text = "Wir haben unsere Kurse nach ihrer gesamten Stundenzahl unterteilt, wähle die für dich passende Kursdauer!"
            buttons = [{'title': 'bis zu 10 Stunden', 'payload': '/inform_coursesearch{"max_duration":"10"}'},
    		{'title': 'maximal 50 Stunden', 'payload': '/inform_coursesearch{"max_duration":"50"}'},
			{'title': 'auch über 50 Stunden', 'payload': '/inform_coursesearch{"max_duration":"51"}'}]
        
            dispatcher.utter_message(text = text, buttons = buttons)
        else:
            text = "Wie umfangreich darf der Kurs insgesamt sein?"
            buttons = [{'title': 'bis zu 10 Stunden', 'payload': '/inform_coursesearch{"max_duration":"10"}'},
    		{'title': 'maximal 50 Stunden', 'payload': '/inform_coursesearch{"max_duration":"50"}'},
			{'title': 'auch über 50 Stunden', 'payload': '/inform_coursesearch{"max_duration":"51"}'}]
        
            dispatcher.utter_message(text = text, buttons = buttons)
        return []

class ActionAskCertificate(Action):
    def name(self):
        return 'action_ask_certificate'

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        intent = str(tracker.get_intent_of_latest_message())
        if intent == 'change_certificate_slot':
            text = "Wie ich verstanden habe, möchtest du einen neuen Nachweis wählen, den du in deinem Wunschkurs erhalten kannst. Wir haben zwei Optionen:"
            buttons = [{'title': 'Teilnahmebescheinigung (unbenotet)', 'payload': '/inform_coursesearch{"certificate":"Teilnahmebescheinigung"}'},
    		{'title': 'Leistungsnachweis (benotet)', 'payload': '/inform_coursesearch{"certificate":"Leistungsnachweis"}'},
			{'title': 'egal', 'payload': '/undecided'}]
        
            dispatcher.utter_message(text = text, buttons = buttons)
        else:
            text = "Welcher Nachweis ist dir wichtig?"
            buttons = [{'title': 'Teilnahmebescheinigung (unbenotet)', 'payload': '/inform_coursesearch{"certificate":"Teilnahmebescheinigung"}'},
    		{'title': 'Leistungsnachweis (benotet)', 'payload': '/inform_coursesearch{"certificate":"Leistungsnachweis"}'},
			{'title': 'egal', 'payload': '/undecided'}]
        
            dispatcher.utter_message(text = text, buttons = buttons)
        return []

class ValidateCourseSearchForm(FormValidationAction):
	def name(self) -> Text:
		return "validate_coursesearch_form"
	
	@staticmethod
	def language_db() -> List[Text]:
		"""Database of supported languages"""
		return ["deutsch", "englisch", "egal"]

	@staticmethod
	def language_no_support_db() -> List[Text]:
		"""Database of not supported languages"""
		return ["spanisch", "französisch", "robotisch", "russisch", "slowakisch", "katalanisch", "tschechisch", "mandarin", "hindi", "niederländisch", "schwedisch"]

	@staticmethod
	def topic_db() -> List[Text]:
		"""Database of topics"""
		return ['ki-einführung', 'ki-vertiefung', 'ki-berufsfelder', 'ki-gesellschaft', 'data science', 'maschinelles lernen', 'egal']
	
	@staticmethod
	def certificate_db() -> List[Text]:
		"""Database of certificates"""
		return ["teilnahmebescheinigung", "leistungsnachweis", "egal"]

	@staticmethod
	def duration_db() -> List[Text]:
		"""Database of durations"""
		return ["0", "10", "50", "51"]
	
	@staticmethod
	def duration_db() -> List[Text]:
		"""Database of levels"""
		return ["einsteiger", "fortgeschritten", "experte"]

	def validate_language(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:
		"""Validate language"""
	
		if slot_value.lower() in self.language_db():
			return {"language": slot_value.lower()}
		elif slot_value.lower() in self.language_no_support_db():
			lang = str(slot_value).capitalize()
			print(lang) # for testing
			dispatcher.utter_message(text = f"Wir bieten auf dem KI-Campus nur Kurse auf Deutsch und Englisch an. Bestimmt ist für dich etwas Passendes dabei!")
			return {"language": None}
		else:
			dispatcher.utter_message(response = "utter_interjection_languages")
			return {"language": None}

	def validate_topic(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:
		"""Validate topic"""	
		if slot_value.lower() in self.topic_db():
			return {"topic": slot_value.lower()}
		else:
			dispatcher.utter_message("Dieses Thema habe ich leider nicht. Damit du einen guten Überblick hast, habe ich dir eine Auswahl unserer Themenkategorien vorbereitet.")
			return {"topic": None}