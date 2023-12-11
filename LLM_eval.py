import datasets
import openai
import os
import time
import sys
import random
import csv
import re
import statistics
import argparse
from datasets import load_dataset, load_dataset_builder, get_dataset_split_names, Dataset
from roundtable import roundTable
import utils
from utils import getResponse, grade_answer, llm_judge

openai.api_key = os.getenv("OPENAI_API_KEY")
#System messages for question answering
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
'judge': """You are a test proctor. You will recieve a question, response and correct answer and you should respond with a number from 1 through 10 that rates how well the response captures the main points of the correct answer where 1 is not at all and 10 is completely.
The following is an example:
Question: What is the meaning of life?
Correct answer: Generally one should seek to improve the world around them by being a good steward of nature and improving the lives of other people.
Response: People should take care of their environment and do their best to help each other

Grade: 10

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

Grade: 1

(((Your responses should always be formatted by two newlines, then the string 'Grade:' followed by the number grade for the given response. Respond with nothing other than what was just detailed.)))""",
'normal_long': "You are taking a test. Provide your answers by responding with one to two sentences.",
'researcher_long': "Act as a researcher with an IQ of 180 that is an expert at problem solving, common sense reasoning, and strategy. You are taking a test. Provide your answers by responding with one to two sentences.",
'persona_long': "You are taking a test. Act as the persona provided and provide your answers by responding with one to two sentences.",
'roundtable_admin_initial_long': "You are taking a test. Provide your answers by responding with one to two sentences as well as separately providing your reasoning for your answer.",
'roundtable_expert_long': "You are {}, also referred to as {}.\n You are assisting the administrator in taking a test by offering useful critique and information. Provide feedback on the most recent answer given by the administrator, as well as their reasoning and offer suggested changes if you think the answer is incorrected, as well as your reasoning why. Pay attention to the feedback of any other experts and correct any incorrect information or suggestions. ((Be succinct. Do not provide overly long feedback. Do not exceed 1500 characters in your response))",
'roundtable_admin_revisor_long': "You are taking a test. Revise the previous answer according to the feedback provided by the experts you are collaborating with.",
'roundtable_admin_decider_long': "You are taking a test. Decide the best answer given the feedback and revisions that have been made. ((Provide your answers by responding with one to two sentences.))",}

def takeTest(dataset_name="commonsense_qa", style="normal", question_limit=100, grading=True, output_file=None, judge_evaluations = 1):
	
	#Initialize logging file
	if output_file:
		recording_file = open(output_file + "_{}_{}_{}_{}questions.csv".format(style, dataset_name, question_limit, utils.model_selection),'w', encoding="utf-8", newline='')
		record = csv.writer(recording_file)
		record.writerow(['Prompt','Answer','Correct answer','Evaluation'])

	#Load and shuffle dataset, select a section based on question limit
	if dataset_name == "commonsense_qa":
		dataset = load_dataset("commonsense_qa", split='train')
	elif dataset_name == "ai2_arc":
		dataset = load_dataset("ai2_arc", 'ARC-Challenge')
	elif dataset_name == "mmlu":
		dataset = load_dataset("cais/mmlu", "all", split="auxiliary_train")
	elif dataset_name == "databricks":
		dataset = load_dataset("databricks/databricks-dolly-15k", split='train')
	elif dataset_name == "LongForm":
		dataset = load_dataset("akoksal/LongForm", split='train')
	else:
		dataset = load_dataset("pubmed_qa", 'pqa_labeled', split='train')

	if dataset_name == "LongForm":
		to_remove = []
		large_count = 0
		for entry in dataset:
			# if entry['subset'] == 'boardgames':
			# 	# print(entry)
			# 	pass
			if len(entry['output']) > 2000 or len(entry['input']) > 2000:
				large_count += 1
				to_remove.append(entry)

		print(large_count)
		# print(dir(dataset))
		dataset = dataset.to_list()
		for entry in to_remove:
			dataset.remove(entry)
		dataset = Dataset.from_list(dataset)
		# sys.exit()

	
	shuffle_seed = random.randint(0,1000)
	shuffled_dataset = dataset.shuffle(seed=shuffle_seed)
	selection = shuffled_dataset.select([i for i in range(min(question_limit, len(shuffled_dataset)))])



	


	correct = 0
	incorrect = 0
	invalid = 0
	aggregate_scores = []
	for row in selection:
		record_row = []
		if dataset_name in ["pubmed_qa","databricks", "LongForm"]:
			choices = ["yes" ,"no", "maybe"]
		else:
			choices = row['choices']
		if dataset_name in ("commonsense_qa", "ai2_arc"):
			choices = choices["text"]
		if dataset_name == "commonsense_qa":
			content = "{} \n1. {} \n2. {} \n3. {} \n4. {} \n5. {}".format(row['question'], choices['text'][0], 
						choices['text'][1], choices['text'][2], choices['text'][3], choices['text'][4])
		elif dataset_name == "pubmed_qa":
			content = ""
			
			for context in row['context']['contexts']:
				content += context
			content += ".\n\n" +row['question'] + "\n"
			
			if not (style[-4:] =="long"):
				for i in range(len(choices)):
					content+= "{}. {} \n".format(i+1, choices[i])
		elif dataset_name == "databricks":
			content = row["context"]
			content += "\n\n" + row["instruction"]

		elif dataset_name == "LongForm":
			content = row["input"]


		else:
			
			content = row['question'] + "\n"
			print(row)
			for i in range(len(choices)):
				content+= "{}. {} \n".format(i+1, choices[i])

		print("Sending question {} of {}".format((correct + incorrect + 1), len(selection)))
		print(content)
		if style == "roundtable":
			LLM_response = roundTable(content, record=record, record_file=recording_file)
		elif style == "roundtable_long":
			LLM_response = roundTable(content, record=record, record_file=recording_file, style="long")
		elif style == "clean_dataset":
			correct = 0
			incorrect = 1
			continue

		else:
	
			if style in ["persona", "persona_long"]:
				if dataset_name in ["LongForm"]:
					persona_content = "Describe a detailed persona of an expert who would be able to answer the following question:\n {}".format(row['input'])
				else:
					persona_content = "Describe a detailed persona of an expert who would be able to answer the following question:\n {}".format(row['question'])
				messages =[
					{"role": "system", "content": "You are an expert at describing personas. Return a detailed description of only the persona that was requested."},
					{"role": "user", "content": persona_content}
				]		
				response = getResponse(messages)
				LLM_response = response
				content = "Act as {} when answering the following question:\n".format(LLM_response) + "\n" + content


			messages =[
					{"role": "system", "content": system_messages[style]},
					{"role": "user", "content": content}
				]

			print("Sending question {} of {}".format((correct + incorrect + 1), len(selection)))
			print(content)
			LLM_response = getResponse(messages)
		grading_style = "long" if style[-4:] == "long" else "mc"
		print(f"grading_style: {grading_style}")
		print(style[-4:])
		if grading_style == "long":
			correct, incorrect, invalid, rating = grade_answer(LLM_response, dataset_name, row, record, content, output_file, correct, incorrect, invalid, style=grading_style, judge_eval_iterations = judge_evaluations)
			aggregate_scores.append(rating)
		else:
			correct, incorrect, invalid = grade_answer(LLM_response, dataset_name, row, record, content, output_file, correct, incorrect, invalid, style=grading_style)


		recording_file.flush()
		time.sleep(3)

	print("""
	Total score: {}/{}
	Percentage: {}
		""".format(correct, (incorrect + correct), str(float(correct)/(incorrect + correct))))
	record.writerow(["Total", "{}/{}".format(correct, (incorrect + correct)), "Percentage", str(float(correct)/(incorrect + correct)),
		"Incorrect", str(incorrect-invalid), "Invalid", str(invalid)])
	if grading_style == "long":
		record.writerow(["Mean score", "{}".format(statistics.mean(aggregate_scores)),
		"Variance", str(statistics.variance(aggregate_scores))])
		print("""
			Mean score: {}
			Variance: {}
				""".format(statistics.mean(aggregate_scores), str(statistics.variance(aggregate_scores))))



if __name__ == "__main__":
	parser = argparse.ArgumentParser(
                    prog='ProgramName',
                    description='What the program does',
                    epilog='Text at the bottom of help')

	parser.add_argument('-q','--questions', action='store', type=int, default=10)
	parser.add_argument('-s','--style', action='store', default='all')
	parser.add_argument('-e','--evaluation_style', action='store', default='long')
	parser.add_argument('-d','--dataset', action='store', default="LongForm")
	parser.add_argument('-f','--file_base', action='store', default="answers")
	parser.add_argument('-m','--model', action='store', default="gpt-3.5-turbo")
	parser.add_argument('-j','--judge_evals', action='store', type=int, default=3)
	args = parser.parse_args()
	
	utils.init()
	utils.model_selection = args.model

	all_styles = ["normal", "researcher", "persona", "roundtable"]
	all_styles_long = ["normal_long", "researcher_long", "persona_long", "roundtable_long"]
	no_roundtable = ["normal", "researcher", "persona", "roundtable"]
	no_roundtable_long = ["normal_long", "researcher_long", "persona_long"]

	question_limit = args.questions
	if args.style == "judge_eval":
		sample_answer = """
		As ILC2s are elevated in patients with CRSwNP, they may drive nasal polyp formation in CRS. 
		ILC2s are also linked with high tissue and blood eosinophilia and have a potential role in the activation and survival of eosinophils during the Th2 immune response. 
		The association of innate lymphoid cells in CRS provides insights into its pathogenesis.
		"""

		sample_wrong_answer = """
		As ILC2s are decreased in patients with CRSwNP, they may prevent nasal polyp formation in CRS. 
		ILC2s are also negatively linked with high tissue and blood eosinophilia and have a potential role in the deactivation of eosinophils during the Th2 immune response.
		The association of innate lymphoid cells in CRS provides no insights into its pathogenesis.
		"""

		sample_right_answer = """
		As ILC2s are increased in patients with CRSwNP, they may encourage nasal polyp formation in CRS. 
		ILC2s are also associated with high tissue and blood eosinophilia and have a potential role in the continuation of eosinophils during the Th2 immune response.
		The association of innate lymphoid cells in CRS reveals insights into its pathogenesis.
		"""

		sample_question="Are group 2 innate lymphoid cells ( ILC2s ) increased in chronic rhinosinusitis with nasal polyps or eosinophilia?"
		judge_wrong_answers = []
		judge_right_answers = []
		for i in range(question_limit):
			judge_wrong_answers.append(int(llm_judge(sample_wrong_answer, sample_question, sample_answer)[-1]))
			judge_right_answers.append(int(llm_judge(sample_right_answer, sample_question, sample_answer)[-1]))
		
		print(judge_wrong_answers)
		print(f"""variance_wrong = {statistics.variance(judge_wrong_answers)}
			mean_wrong = {statistics.mean(judge_wrong_answers)}""")

		print(judge_right_answers)
		print(f"""variance_right = {statistics.variance(judge_right_answers)}
			mean_right = {statistics.mean(judge_right_answers)}""")
		sys.exit()

	if args.evaluation_style =="mc":
		if args.style.lower() == "all":
			styles = all_styles
		elif args.style.lower() == "no_roundtable":
			styles = no_roundtable
		else:
			styles = [args.style.lower()]
		for style in styles:
				takeTest(style=style, question_limit = question_limit, output_file = "output/" + args.file_base, dataset_name=args.dataset, judge_evaluations = args.judge_evals)

	else:
		if args.style.lower() == "all":
			styles = all_styles_long
			
		elif args.style.lower() == "no_roundtable":
			styles = no_roundtable_long
		else:
			styles = [args.style.lower() + "_long"]
		for style in styles:
				takeTest(style=style, question_limit = question_limit, output_file = "output/" + args.file_base, dataset_name=args.dataset, judge_evaluations = args.judge_evals)
	

