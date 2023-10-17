import datasets
import openai
import os
import time
import sys
import random
import csv
import re
from datasets import load_dataset, load_dataset_builder, get_dataset_split_names

openai.api_key = os.getenv("OPENAI_API_KEY")
answer_dicts = {"commonsense_qa":{'A': 1, 'B': 2, 'C': 3, 'D': 4, 'E': 5}}
#System messages for question answering
system_messages = {'normal': "You are taking a test. Provide your answers by responding only with the number of the appropriate answer for the presented question",
'researcher': "Act as a researcher with an IQ of 180 that is an expert at problem solving, common sense reasoning, and strategy. You are taking a test. Provide your answers by responding only with the number of the appropriate answer for the presented question,",
'persona': "You are taking a test. Act as the persona provided and provide your answers by responding only with the number of the appropriate answer for the presented question",
'roundtable_admin_initial': "You are taking a test. Provide your answers by responding with the number of the appropriate answer for the presented question as well as your reasoning for choosing it.",
'roundtable_expert': "You are {}, also referred to as {}.\n You are assisting the administrator in taking a test by offering useful critique and information. Provide feedback on the most recent answer given by the administrator, as well as their reasoning and offer suggested changes if you think the answer is incorrected, as well as your reasoning why. ((Be succinct and only suggest answers that are provided by the question. Do not provide overly long feedback.))",
'roundtable_admin_revisor': "You are taking a test. Revise the previous answer according to the feedback provided by the experts you are collaborating with. ((You are not allowed to change the answers to the question, only the choice of answer you make.))",
'roundtable_admin_decider': "You are taking a test. Decide the best answer given the feedback and revisions that have been made. ((Provide your answers by responding only with the number of the appropriate answer for the presented question.))",
'roundtable_creator':"""You are an expert at creating useful personas. You create detailed personas of useful experts for answering the questions you are given.
	((When you return the personas, be sure to seperate them with a sequence of two newlines, followed by 5 dashes, followed by two newlins. For example:
	Persona description 1

	-----

	Persona description 2))
	"""}

def getResponse(messages):
	successful_response = False
	current_time = 2
	time_max = 60
	tries = 0
	while not successful_response:
		try:
			response = openai.ChatCompletion.create(
				model="gpt-3.5-turbo",
				messages=messages
			)
			successful_response = True
		except Exception as e:
			# print(e)
			print("Retrying after time: {}".format(current_time))
			time.sleep(current_time)

			current_time **= 2
			current_time = min(current_time, time_max)
			tries += 1
			if tries > 4:
				print("Max tries exceeded")
				sys.exit()
	# time.sleep(4)
	return response['choices'][0]['message']['content']

def roundTable(question, number_of_experts = 2, rounds = 2, record = None):
	#Create a set of personas to help critique answers to the following question
	# system_message_creator = """You are an expert at creating useful personas. You create detailed personas of useful experts for answering the questions you are given.
	# ((When you return the personas, be sure to seperate them with a sequence of two newlines, followed by 5 dashes, followed by two newlins. An example of this follows))
	# Expert description 1

	# -----

	# Expert description 2
	# """

	messages =[
				{"role": "system", "content": system_messages['roundtable_creator']},
				{"role": "user", "content": "Describe {} detailed persona(s) of (an) expert(s) who would be able to answer the following question:\n {}".format(number_of_experts, question)}
			]
	response = getResponse(messages)
	print("Initial experts response:")
	print(response)
	# sys.exit()

	# experts_choices = [response.split("Persona "), response.split("Expert "), response.split("-----"), response.split("")]

	experts = response.split("-----")

	print(question)
	for i in range(len(experts)):
		print(experts[i])
		if record:
			record.writerow(["Expert {}".format(i), experts[i]])
		# sys.exit()


	



	#Perform a round table analysis
	admin_messages =[
				{"role": "system", "content": system_messages['roundtable_admin_initial']},
				{"role": "user", "content": question}
			]
	print("getting initial answer")
	initial_answer = getResponse(admin_messages)
	if record:
			record.writerow(["initial_answer", initial_answer])
	print(initial_answer)
	admin_messages.append({"role": "assistant", "content": "Administrator: " + initial_answer})
	expert_message_logs = []
	for i in range(len(experts)):
		messages = [
			{"role": "system", "content": system_messages['roundtable_expert'].format(experts[i], "Expert {}".format(i))},
			{"role": "user", "content": "Administrator: The question being answered is:\n{}".format(question)},
			{"role": "assistant", "content": "Administrator: " + initial_answer}
		]
		expert_message_logs.append(messages)
	admin_messages[-1]['content'] = system_messages['roundtable_admin_revisor']
	for i in range(rounds):
		for j in range(len(experts)):
			print("getting expertResponse")
			expertResponse = getResponse(expert_message_logs[j])
			if record:
				record.writerow(["Expert {} round {} feedback".format(j,i), expertResponse])
			print(expertResponse)
			for expert_message_log in expert_message_logs:
				expert_message_log.append({"role": "assistant", "content": "Expert {}:".format(j) + expertResponse})
			admin_messages.append({"role": "assistant", "content": "Expert {}:".format(j) + expertResponse})
		print("getting revised answer")
		revised_answer = getResponse(admin_messages)
		if record:
				record.writerow(["Round {} revised answer".format(i), revised_answer])
		print(revised_answer)
		for expert_message_log in expert_message_logs:
				expert_message_log.append({"role": "assistant", "content": "Administrator: " + revised_answer})

	

	#show conversation
	for message in admin_messages:
		print(message['content'])

	admin_messages[-1]['content'] = system_messages['roundtable_admin_decider']

	#Create a final answer
	admin_messages.append({"role": "user", "content": "Return only the number of the final revised_answer answer."})
	final_answer = getResponse(admin_messages)
	if record:
				record.writerow(["Final answer after {} rounds".format(rounds), revised_answer])
	return final_answer


def takeTest(dataset_name="commonsense_qa", style="normal", question_limit=100, grading=True, output_file=None):
	
	#Initialize logging file
	if output_file:
		record = csv.writer(open(output_file + "_{}.csv".format(style), 'w', newline=''))
		record.writerow(['Prompt','Answer','Correct answer','Evaluation'])
	#For ease of processing
	answer_dict = answer_dicts[dataset_name]

	#Load and shuffle dataset, select a section based on question limit
	dataset = load_dataset("commonsense_qa", split='train')
	shuffle_seed = random.randint(0,1000)
	shuffled_dataset = dataset.shuffle(seed=shuffle_seed)
	selection = shuffled_dataset.select([i for i in range(min(question_limit, len(shuffled_dataset)))])

	


	correct = 0
	incorrect = 0
	invalid = 0
	for row in selection:
		record_row = []
		choices = row['choices']
		content = "{} \n1. {} \n2. {} \n3. {} \n4. {} \n5. {}".format(row['question'], choices['text'][0], 
					choices['text'][1], choices['text'][2], choices['text'][3], choices['text'][4])
		if style == "roundtable":
			LLM_response = roundTable(content, record=record)

		else:
	
			if style == "persona":
					persona_content = "Describe a detailed persona of an expert who would be able to answer the following question:\n {}".format(row['question'])
					messages =[
						{"role": "system", "content": "You are an expert at describing personas. Return a detailed description of only the persona that was requested."},
						{"role": "user", "content": persona_content}
					]		
					response = getResponse(messages)
					LLM_response = response['choices'][0]['message']['content']
					content = "Act as {} when answering the following question:\n".format(LLM_response) + "\n" + content


			# if content:
			# 	content += "{} \n1. {} \n2. {} \n3. {} \n4. {} \n5. {}".format(row['question'], choices['text'][0], 
			# 		choices['text'][1], choices['text'][2], choices['text'][3], choices['text'][4])
			# else:
			# 	content = "{} \n1. {} \n2. {} \n3. {} \n4. {} \n5. {}".format(row['question'], choices['text'][0], 
			# 		choices['text'][1], choices['text'][2], choices['text'][3], choices['text'][4])

			messages =[
					{"role": "system", "content": system_messages[style]},
					{"role": "user", "content": content}
				]

			print("Sending question {} of {}".format((correct + incorrect + 1), len(selection)))
			print(content)
			LLM_response = getResponse(messages)
		# LLM_response = response
		numbers = re.findall(r'\d+', LLM_response)
		LLM_answer = -1
		if not (numbers == []) and grading:
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
				record.writerow([content,LLM_response, answer_dict[row['answerKey']], False])
		else:
			is_correct = LLM_answer == answer_dict[row['answerKey']]
			if output_file:
				record.writerow([content,LLM_response, answer_dict[row['answerKey']], is_correct])

		print(LLM_answer)
		print(answer_dict[row['answerKey']])

		if is_correct:
			correct += 1
			print("Correct!\n")
		else:
			incorrect += 1
			print("Incorrect!\n")
		time.sleep(3)

	print("""
	Total score: {}/{}
	Percentage: {}
		""".format(correct, (incorrect + correct), str(float(correct)/(incorrect + correct))))
	record.writerow(["Total", "{}/{}".format(correct, (incorrect + correct)), "Percentage", str(float(correct)/(incorrect + correct)),
	"Incorrect", str(incorrect-invalid), "Invalid", str(invalid)])


if __name__ == "__main__":
	question_limit = int(sys.argv[1])
	if sys.argv[2].lower() == "all":
		styles = ["normal", "researcher", "persona", "roundtable"]
		for style in styles:
			takeTest(style=style, question_limit = question_limit, output_file = "answers")
	else:
		takeTest(style=sys.argv[2].lower(), question_limit = question_limit, output_file = "answers")

