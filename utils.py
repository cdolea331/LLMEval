import time
import openai
import re
import statistics
import os
from openai import OpenAI
answer_dicts = dict.fromkeys(['commonsense_qa', 'ai2_arc', 'mmlu', 'databricks', 'databricks_sub', "LongForm", "FinTalk"], {'A': 1, 'B': 2, 'C': 3, 'D': 4, 'E': 5, '1': 1, '2': 2, '3': 3, '4': 4, '5': 5, '0':0})
answer_dicts["pubmed_qa"] = {"yes": 1, "no": 2, "maybe": 3}
client = OpenAI(
  api_key=os.environ['OPENAI_API_KEY'],  # this is also the default, it can be omitted
)


system_messages = {'normal': "You are taking a test. Provide your answers by responding only with the number of the appropriate answer for the presented question",
'researcher': "Act as a researcher with an IQ of 180 that is an expert at problem solving, common sense reasoning, and strategy. You are taking a test. Provide your answers by responding only with the number of the appropriate answer for the presented question,",
'persona': "You are taking a test. Act as the persona provided and provide your answers by responding only with the number of the appropriate answer for the presented question",
'roundtable_admin_initial': "You are taking a test. Provide your answers by responding with the number of the appropriate answer for the presented question as well as your reasoning for choosing it.",
'roundtable_expert': "You are {}, also referred to as {}.\n You are assisting the administrator in taking a test by offering useful critique and information. Provide feedback on the most recent answer given by the administrator, as well as their reasoning and offer suggested changes if you think the answer is incorrected, as well as your reasoning why. Pay attention to the feedback of any other experts and correct any incorrect information or suggestions. ((Be succinct and only suggest answers that are provided by the question. Do not provide overly long feedback. Do not exceed 1500 characters in your response))",
'roundtable_admin_revisor': "You are taking a test. Revise the previous answer according to the feedback provided by the experts you are collaborating with. ((You are not allowed to change the answers to the question, only the choice of answer you make.))",
'roundtable_admin_decider': "You are taking a test. Decide the best answer given the feedback and revisions that have been made. ((Provide your answers by responding only with the number of the appropriate answer for the presented question.))",
'roundtable_creator':"""You are an expert at creating useful personas. You create detailed personas of useful experts for answering the questions you are given.
	((When you return the personas, be sure to seperate them with a sequence of two newlines, followed by 5 dashes, followed by two newlines. For example:
	Persona description 1

	-----

	Persona description 2))
	""",
'clean_dataset': "nothing",
'judge': """You are a test proctor. You will recieve a question, response and correct answer and you should respond with a number from 0 through 9 that rates how well the response captures the main points of the correct answer where 1 is not at all and 9 is completely.
The following is an example:
Question: What is the meaning of life?
Correct answer: Generally one should seek to improve the world around them by being a good steward of nature and improving the lives of other people.
Response: People should take care of their environment and do their best to help each other

Grade: 9

Another example with the same question follows:
Question: What is the meaning of life?
Correct answer: Generally one should seek to improve the world around them by being a good steward of nature and improving the lives of other people.
Response: People should be good to each other

Grade: 6

Another example with the same question follows:
Question: What is the meaning of life?
Correct answer: Generally one should seek to improve the world around them by being a good steward of nature and improving the lives of other people.
Response: Doing what makes you feel good

Grade: 3

Another example with the same question follows:
Question: What is the meaning of life?
Correct answer: Generally one should seek to improve the world around them by being a good steward of nature and improving the lives of other people.
Response: Breaking rocks

Grade: 0

(((Your responses should always be formatted by two newlines, then the string 'Grade:' followed by the number grade for the given response. Respond with nothing other than what was just detailed.)))""",
'normal_long': "You are taking a test. Provide your answers by responding with one to two sentences.",
'researcher_long': "Act as a researcher with an IQ of 180 that is an expert at problem solving, common sense reasoning, and strategy. You are taking a test. Provide your answers by responding with one to two sentences.",
'persona_long': "You are taking a test. Act as the persona provided and provide your answers by responding with one to two sentences.",
'roundtable_admin_initial_long': "You are taking a test. Provide your answers by responding with one to two sentences as well as separately providing your reasoning for your answer.",
'roundtable_expert_long': "You are {}, also referred to as {}.\n You are assisting the administrator in taking a test by offering useful critique and information. Provide feedback on the most recent answer given by the administrator, as well as their reasoning and offer suggested changes if you think the answer is incorrected, as well as your reasoning why. Pay attention to the feedback of any other experts and correct any incorrect information or suggestions. ((Be succinct. Do not provide overly long feedback. Do not exceed 1500 characters in your response))",
'roundtable_admin_revisor_long': "You are taking a test. Revise the previous answer according to the feedback provided by the experts you are collaborating with.",
'roundtable_admin_decider_long': "You are taking a test. Decide the best answer given the feedback and revisions that have been made. ((Provide your answers by responding with one to two sentences.))",}

def init():
	global model_selection
	model_selection = ""


def getResponse(messages, model="gpt-3.5-turbo"):
	successful_response = False
	current_time = 2
	time_max = 60
	tries = 0
	if model == "gpt-3.5-turbo":
		#global model_selection defined in LLM_eval.py
		model = model_selection
	while not successful_response:
		try:
			response = client.chat.completions.create(

				model=model,
				messages=messages
			)
			successful_response = True
		except Exception as e:
			print(e)
			print("Retrying after time: {}".format(current_time))
			print(messages)
			time.sleep(current_time)

			current_time **= 2
			current_time = min(current_time, time_max)
			tries += 1
			if tries > 4:
				print("Max tries exceeded")
				sys.exit()
	# time.sleep(4)
	# print(response.choices[0].message.content)
	return response.choices[0].message.content[:2000]

def llm_judge(response, question, answer):
	messages = messages =[
				{"role": "system", "content": system_messages['judge']},
				{"role": "user", "content": """Question:{}


				Correct Answer:{}


				Response:{}""".format(question, answer, response)}
			]

	judge_response = getResponse(messages, model="gpt-4")

	return judge_response


def grade_answer(LLM_response, dataset_name, row, record, content, output_file, correct, incorrect, invalid, style="mc", judge_eval_iterations = 1):

	answer_dict = answer_dicts[dataset_name]
	
	LLM_answer = -1
	if dataset_name in ("commonsense_qa", "ai2_arc"):
		correct_answer = answer_dict[row['answerKey']]
	elif dataset_name in ("mmlu"):
		correct_answer = answer_dict[str(row['answer'])]
	elif dataset_name in ("pubmed_qa"):
		correct_answer = answer_dict[str(row["final_decision"])]

	if style =="mc":
		numbers = re.findall(r'\d+', LLM_response)
		is_correct = False
		if numbers != []:
			for number in numbers:
				if int(number) < 6 and int(number) > 0:
					LLM_answer = int(number)
					break

		if LLM_answer == -1:
			incorrect += 1
			invalid += 1
			print("Invalid answer:")
			print(LLM_response)
			if output_file:
				record.writerow([content,LLM_response, correct_answer, False])
		else:
			if dataset_name == "mmlu":
				LLM_answer = int(LLM_answer) - 1
			is_correct = LLM_answer == correct_answer

		if is_correct:
			correct += 1
			print("Correct!\n")
		else:
			incorrect += 1
			print("Incorrect!\n")

		print(LLM_answer)
		print(correct_answer)
		if output_file:
			record.writerow([content,LLM_response, correct_answer, is_correct])

		
		return (correct, incorrect, invalid)


	elif style == "long":
		if dataset_name in ("pubmed_qa"):
			correct_answer = row['long_answer']
		elif dataset_name in ["databricks", "databricks_sub"]:
			correct_answer = row['response']
		elif dataset_name in ["LongForm"]:
			correct_answer = row['output']
		elif dataset_name in ["FinTalk"]:
			correct_answer = row['response']
		evaluations = []
		for i in range(judge_eval_iterations):

			judge_response = llm_judge(LLM_response, content, correct_answer)
			print(judge_response)
			numbers = re.findall(r'\d+', judge_response)
			if numbers != []:
				rating = int(numbers[0])
			else:
				rating = 1
			if rating > 5:
				correct += 1
				# print("Correct!\n")
			else:
				incorrect += 1
				# print("Incorrect!\n")

			is_correct = rating
			evaluations.append(rating)
		if len(evaluations) > 1:
			pruned = []
			prune_max = 0
			for entry in evaluations:
				eval_copy = [x for x in evaluations]
				eval_copy.remove(entry)
				mean_diff = abs(statistics.mean(eval_copy) - entry)
				if mean_diff > prune_max:
					pruned = eval_copy
					prune_max = mean_diff

			mean = statistics.mean(eval_copy)
			variance = statistics.variance(eval_copy)
		else:
			eval_copy = evaluations
			mean = evaluations[0]
			variance = 0
				


		

		if output_file:
			record.writerow([content,LLM_response, correct_answer, mean, mean, variance])

		
		return (correct, incorrect, invalid, rating)