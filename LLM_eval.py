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
		except:
			print("Retrying after time: {}".format(current_time))
			time.sleep(current_time)

			current_time **= 2
			current_time = max(current_time, time_max)
			tries += 1
			if tries > 4:
				print("Max tries exceeded")
				sys.exit()
	return response


def takeTest(dataset_name="commonsense_qa", style="normal", question_limit=100, grading=True, output_file=None):
	if output_file:
		record = csv.writer(open(output_file + "_{}.csv".format(style), 'w', newline=''))
		record.writerow(['Prompt','Answer','Correct answer','Evaluation'])
	answer_dict = answer_dicts[dataset_name]

	dataset = load_dataset("commonsense_qa", split='train')
	shuffle_seed = random.randint(0,1000)
	shuffled_dataset = dataset.shuffle(seed=shuffle_seed)
	selection = shuffled_dataset.select([i for i in range(min(question_limit, len(shuffled_dataset)))])
	system_messages = {'normal': "You are taking a test. Provide your answers by responding only with the number of the appropriate answer for the presented question",
	'researcher': "Act as a researcher with an IQ of 180 that is an expert at problem solving, common sense reasoning, and strategy. You are taking a test. Provide your answers by responding only with the number of the appropriate answer for the presented question,",
	'persona': "You are taking a test. Act as the persona provided and provide your answers by responding only with the number of the appropriate answer for the presented question"}


	correct = 0
	incorrect = 0
	invalid = 0
	for row in selection:
		record_row = []
		choices = row['choices']
		content = None

	
		if style == "persona":
				content = "Describe a detailed persona of an expert who would be able to answer the following question:\n"
				messages =[
					{"role": "system", "content": "You are an expert at describing personas. Return a detailed description of only the persona that was requested."},
					{"role": "user", "content": content}
				]		
				response = getResponse(messages)
				LLM_response = response['choices'][0]['message']['content']
				content = "Act as {} when answering the following question:\n".format(LLM_response)


		if content:
			content += "{} \n1. {} \n2. {} \n3. {} \n4. {} \n5. {}".format(row['question'], choices['text'][0], 
				choices['text'][1], choices['text'][2], choices['text'][3], choices['text'][4])
		else:
			content = "{} \n1. {} \n2. {} \n3. {} \n4. {} \n5. {}".format(row['question'], choices['text'][0], 
				choices['text'][1], choices['text'][2], choices['text'][3], choices['text'][4])

		messages =[
				{"role": "system", "content": system_messages[style]},
				{"role": "user", "content": content}
			]

		print("Sending question {} of {}".format((correct + incorrect + 1), len(selection)))
		print(content)
		response = getResponse(messages)
		LLM_response = response['choices'][0]['message']['content']
		numbers = re.findall(r'\d+', LLM_response)
		LLM_answer = -1
		if not (numbers == []):
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
	styles = ["normal", "researcher", "persona"]
	question_limit = int(sys.argv[1])
	for style in styles:
		takeTest(style=style, question_limit = question_limit, output_file = "answers")
