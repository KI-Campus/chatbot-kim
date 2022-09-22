import os
from typing import Text, Dict, Any, List

from rasa_sdk import Action, Tracker
from rasa_sdk.events import SlotSet

import requests
import json

import random
import itertools

from rasa_sdk import FormValidationAction
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import Restarted
from rasa_sdk.types import DomainDict

from .settings import get_recommender_config


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

	service_url: str
	service_token: str

	def __init__(self):
		# service_config_path = os.path.join(os.path.dirname(__file__), '..', 'kic_recommender.yml')
		# NOTE will print error message if file is missing:
		recommender_config = get_recommender_config()  # endpoints.read_endpoint_config(service_config_path, "recommender_api")

		self.service_url = recommender_config['url']
		self.service_token = recommender_config['token']

		# DEBUG output TODO remove after testing
		if recommender_config and recommender_config['url'] and recommender_config['token']:
			print("\n  endpoint config: {0}\n".format(recommender_config))
		else:
			print("\n  endpoint config: NO CONFIGURATION FOR RECOMMENDER (recommender_api)\n")

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

		# to do: maybe option 2 implement after delete slot value

		# FIXME DEBUG: show search/filter parameters
		debug_info_msg = "\n  language {0} | topic {1} | level {2} | max_duration {3} | certificate {4} | " \
						 "enrollments {5} | course_visits {6} | search_terms {7}\n".format(
							language, topic, level, max_duration, certificate, enrollments, course_visits, search_terms
						 )
		dispatcher.utter_message(text="Suche Lernangebote für folgende Parameter:" + debug_info_msg)

		r = requests.get('{0}filtered_recommendation_learnings/'.format(self.service_url),
			headers={
				"content-type": "application/json",
				"Authorization": 'Token {0}'.format(self.service_token),
			},
			params={
				"language": language,
				"topic": topic,
				"level": level,
				"max_duration": str(max_duration),
				"certificate": certificate,
				"enrollments": enrollments,
				"course_visits": course_visits,
				"search_terms": search_terms,
			})
		status = r.status_code
		if status == 200:
			response = json.loads(r.content)
			if len(response) < 1:
				dispatcher.utter_message('Leider konnte ich keinen Kurs für diese Parameter finden.')
			else:
				size = len(response)
				limit = min(size, 3)
				dispatcher.utter_message('Also, ich empfehle dir folgende Kurse ({0}): '.format(size))
				button_group = []
				for course in response[0:limit]:
					title = course['name']
					button_group.append({"title": title, "payload": '{0}'.format(title)})
				dispatcher.utter_message(buttons=button_group)
				if limit < size:
					rest = size - limit
					mult_msg = "weiterer Kurs" if rest == 1 else "weitere Kurse"
					dispatcher.utter_message("... und {0} {1}".format(rest, mult_msg))
		elif status == 401:  # Status-Code 401 Unauthorized: wrong access token setting in kic_recommender.yml!
			dispatcher.utter_message('Leider gab es einen Fehler beim Zugriff auf die Kurse, bitte wende dich an den Administrator (Status 401).')
			# FIXME DEBUG:
			dispatcher.utter_message('Fehlerantwort (Status '+str(r.status_code)+'):\n  Headers: '+str(r.headers)+')\n  Body: ' + str(r.content))
		elif status == 404:  # Status-Code 404 None
			dispatcher.utter_message('Leider wurde kein Kurs für diese Parameter gefunden.')
			# FIXME DEBUG:
			dispatcher.utter_message('Fehlerantwort (Status '+str(r.status_code)+'):\n  Headers: '+str(r.headers)+')\n  Body: ' + str(r.content))
		elif status == 500:  # Status-Code 500 Invalid Parameter
			dispatcher.utter_message('Es gab einen Fehler bei der Abfrage.')
			# FIXME DEBUG:
			dispatcher.utter_message('Fehlerantwort (Status '+str(r.status_code)+'):\n  Headers: '+str(r.headers)+')\n  Body: ' + str(r.content))
		else:
			dispatcher.utter_message('Es gab einen Fehler bei der Abfrage, bitte wende dich an den Administrator. Fehler: ' + str(r.content))
			# FIXME DEBUG:
			dispatcher.utter_message('Fehlerantwort (Status '+str(r.status_code)+'):\n  Headers: '+str(r.headers)+')\n  Body: ' + str(r.content))

		return [SlotSet("recommendations", response)]

class ActionAdditionalLearningRecommendation(Action):

	def name(self) -> Text:
		return "action_additional_learning_recommendation"

	def run(self, dispatcher: CollectingDispatcher,
			tracker: Tracker,
			domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

		recommendations = tracker.get_slot("recommendations")
		if len(recommendations) <= 3:
			dispatcher.utter_message('Leider konnte ich keine weitere Empfehlungen zu deinen Suchparametern finden.')
		else:
			recommendations = recommendations[3:]
			size = len(recommendations)
			limit = min(size, 3)
			dispatcher.utter_message('Also, ich empfehle dir folgende Kurse ({0}): '.format(size))
			button_group = []
			for course in recommendations[0:limit]:
				title = course['name']
				button_group.append({"title": title, "payload": '{0}'.format(title)})
			dispatcher.utter_message(buttons=button_group)
			if limit < size:
				rest = size - limit
				mult_msg = "weiterer Kurs" if rest == 1 else "weitere Kurse"
				dispatcher.utter_message("... und {0} {1}".format(rest, mult_msg))

		return [SlotSet("recommendations", recommendations)]

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
		elif  intent == 'start_coursesearch_form': return [SlotSet("language", None), SlotSet("topic", None), SlotSet("level", None), SlotSet("max_duration", None), SlotSet("certificate", None)]
		else:  return []

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
			buttons = [{'title': 'Deutsch', 'payload': '/inform{"language":"Deutsch"}'},
				{'title': 'Englisch', 'payload': '/inform{"language":"Englisch"}'},
				{'title': 'Beide Sprachen', 'payload': '/undecided'}]
			dispatcher.utter_message(text = text, buttons = buttons)
		# default question
		else:
			text = "Soll der Kurs auf Deutsch oder auf Englisch sein?"
			buttons = [{'title': 'Deutsch', 'payload': '/inform{"language":"Deutsch"}'},
				{'title': 'Englisch', 'payload': '/inform{"language":"Englisch"}'},
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
			buttons = [{'title': 'Einführung in die KI', 'payload': '/inform{"topic":"ki-einführung"}'},
				{'title': 'Vertiefung einzelner Themenfelder der KI', 'payload': '/inform{"topic":"ki-vertiefung"}'},
				{'title': 'KI in Berufsfeldern', 'payload': '/inform{"topic":"ki-berufsfelder"}'},
				{'title': 'KI und Gesellschaft', 'payload': '/inform{"topic":"ki-gesellschaft"}'},
				{'title': 'Data Science', 'payload': '/inform{"topic":"Data Science"}'},
				{'title': 'Maschinelles Lernen', 'payload': '/inform{"topic":"Maschinelles Lernen"}'},
				{'title': 'egal', 'payload': '/undecided'}]
			dispatcher.utter_message(text = text, buttons = buttons)
		else:
			text = "Worum soll es in deinem Wunsschkurs gehen? Wähle eins der folgenden Themenfelder!"
			buttons = [{'title': 'Einführung in die KI', 'payload': '/inform{"topic":"ki-einführung"}'},
				{'title': 'Vertiefung einzelner Themenfelder der KI', 'payload': '/inform{"topic":"ki-vertiefung"}'},
				{'title': 'KI in Berufsfeldern', 'payload': '/inform{"topic":"ki-berufsfelder"}'},
				{'title': 'KI und Gesellschaft', 'payload': '/inform{"topic":"ki-gesellschaft"}'},
				{'title': 'Data Science', 'payload': '/inform{"topic":"Data Science"}'},
				{'title': 'Maschinelles Lernen', 'payload': '/inform{"topic":"Maschinelles Lernen"}'},
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
			buttons = [{'title': 'Anfänger*in', 'payload': '/inform{"level":"Anfänger"}'},
			{'title': 'Fortgeschrittene*r', 'payload': '/inform{"level":"Fortgeschritten"}'},
			{'title': 'Experte', 'payload': '/inform{"level":"Experte"}'}]

			dispatcher.utter_message(text = text, buttons = buttons)
		else:
			text = "Wie schätzt du deine Vorkenntnisse im Bereich KI ein?"
			buttons = [{'title': 'Anfänger*in', 'payload': '/inform{"level":"Anfänger"}'},
			{'title': 'Fortgeschrittene*r', 'payload': '/inform{"level":"Fortgeschritten"}'},
			{'title': 'Experte', 'payload': '/inform{"level":"Experte"}'}]

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
			buttons = [{'title': 'bis zu 10 Stunden', 'payload': '/inform{"max_duration":"10"}'},
			{'title': 'maximal 50 Stunden', 'payload': '/inform{"max_duration":"50"}'},
			{'title': 'auch über 50 Stunden', 'payload': '/inform{"max_duration":"51"}'}]

			dispatcher.utter_message(text = text, buttons = buttons)
		else:
			text = "Wie umfangreich darf der Kurs insgesamt sein?"
			buttons = [{'title': 'bis zu 10 Stunden', 'payload': '/inform{"max_duration":"10"}'},
			{'title': 'maximal 50 Stunden', 'payload': '/inform{"max_duration":"50"}'},
			{'title': 'auch über 50 Stunden', 'payload': '/inform{"max_duration":"51"}'}]

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
			buttons = [{'title': 'Teilnahmebescheinigung (unbenotet)', 'payload': '/inform{"certificate":"Teilnahmebescheinigung"}'},
			{'title': 'Leistungsnachweis (benotet)', 'payload': '/inform{"certificate":"Leistungsnachweis"}'},
			{'title': 'egal', 'payload': '/undecided'}]

			dispatcher.utter_message(text = text, buttons = buttons)
		else:
			text = "Welcher Nachweis ist dir wichtig?"
			buttons = [{'title': 'Teilnahmebescheinigung (unbenotet)', 'payload': '/inform{"certificate":"Teilnahmebescheinigung"}'},
			{'title': 'Leistungsnachweis (benotet)', 'payload': '/inform{"certificate":"Leistungsnachweis"}'},
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
	def duration_db() -> List[Text]:
		"""Database of durations"""
		return ["0", "10", "50", "51"]

	@staticmethod
	def levels_db() -> List[Text]:
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
			# test for variable
			dispatcher.utter_message(text = f"Wir bieten auf dem KI-Campus keine Kurse auf {lang} an. Bestimmt ist für dich etwas Passendes auf Deutsch oder Englisch dabei!")
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
			dispatcher.utter_message(response = "utter_unavailable_topic")
			return {"topic": None}
