
from utils import getResponse

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

def roundTable(question, number_of_experts = 2, rounds = 2, record = None, record_file = None, style = "mc"):
	if style == "mc":
		creator_system = 'roundtable_creator'
		admin_system = 'roundtable_admin_initial'
		revisor_system = 'roundtable_admin_revisor'
		expert_system = 'roundtable_expert'
		decider_system = 'roundtable_admin_decider'
	elif style == "long":
		creator_system = 'roundtable_creator'
		admin_system = 'roundtable_admin_initial_long'
		revisor_system = 'roundtable_admin_revisor_long'
		expert_system = 'roundtable_expert_long'
		decider_system = 'roundtable_admin_decider_long'


	messages =[
				{"role": "system", "content": system_messages[creator_system]},
				{"role": "user", "content": "Describe {} detailed persona or personas of an expert or experts who would be able to answer the following question:\n {}".format(number_of_experts, question)}
			]
	response = getResponse(messages)
	print("Initial experts response:")
	# print(response)
	# sys.exit()

	expert_splits = [response.split("Persona "), response.split("Expert "), response.split("-----")]
	min_diff = 999999
	experts = None
	for expert_split in expert_splits:
		diff = abs(number_of_experts-len(expert_split))
		if diff < min_diff:
			min_diff = diff
			experts = expert_split
	# experts = response.split("-----\n")


	# print(question)
	for i in range(len(experts)):
		# print(experts[i])
		if record:
			record.writerow(["Expert {}".format(i), experts[i]])
			# recording_file.flush()
		# sys.exit()


	



	#Perform a round table analysis
	admin_messages =[
				{"role": "system", "content": system_messages[admin_system]},
				{"role": "user", "content": question}
			]
	print("getting initial answer")
	initial_answer = getResponse(admin_messages)
	if record:
			record.writerow(["initial_answer", initial_answer])
	# print(initial_answer)
	admin_messages.append({"role": "assistant", "content": "Administrator: " + initial_answer})
	expert_message_logs = []
	print("Num of experts: {}".format(len(experts)))
	for i in range(len(experts)):
		messages = [
			{"role": "system", "content": system_messages[expert_system].format(experts[i], "Expert {}".format(i))},
			{"role": "user", "content": "Administrator: The question being answered is:\n{}".format(question)},
			{"role": "assistant", "content": "Administrator: " + initial_answer}
		]
		expert_message_logs.append(messages)
	admin_messages[-1]['content'] = system_messages[revisor_system]
	for i in range(rounds):
		for j in range(len(experts)):
			# print("getting expertResponse")
			expertResponse = getResponse(expert_message_logs[j])
			if record:
				record.writerow(["Expert {} round {} feedback".format(j,i), expertResponse])
			# print(expertResponse)
			for expert_message_log in expert_message_logs:
				expert_message_log.append({"role": "assistant", "content": "Expert {}:".format(j) + expertResponse})
			admin_messages.append({"role": "assistant", "content": "Expert {}:".format(j) + expertResponse})
		print("getting revised answer")
		revised_answer = getResponse(admin_messages)
		if record:
				record.writerow(["Round {} revised answer".format(i), revised_answer])
		# print(revised_answer)
		for expert_message_log in expert_message_logs:
				expert_message_log.append({"role": "assistant", "content": "Administrator: " + revised_answer})

	

	#show conversation
	# for message in admin_messages:
		# print(message['content'])

	admin_messages[-1]['content'] = system_messages[decider_system]

	#Create a final answer
	final_answer = getResponse(admin_messages)
	if record:
				record.writerow(["Final answer after {} rounds".format(rounds), revised_answer])
				record_file.flush()
	return final_answer

