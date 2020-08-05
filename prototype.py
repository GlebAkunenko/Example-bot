import json, os
import time as t
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
from vk_api import *
from random import randint, choice
from threading import Thread, Lock

vk = VkApi(token=os.environ.get("TOKEN"))
vk._auth_token()


def timer(user_id, time):
	t.sleep(time)
	locker.acquire()
	score[user_id] = 5
	locker.release()

def random_word(user_id, random_id):
	global score, lottery
	local_vk = VkApi(token=os.environ.get("TOKEN"))
	local_vk._auth_token()
	moon = ['🌑', '🌒', '🌓', '🌔', '🌕', '🌖', '🌗', '🌘']
	locker.acquire()
	s = score[user_id]
	locker.release()
	message_id = local_vk.method('messages.send', {'user_id': user_id, 'random_id': random_id, 'message': 'Ищем рандомное слово ' + moon[0]})
	for x in range(1, randint(9, 14)):
		local_vk.method('messages.edit', {'user_id': user_id, 'peer_id': user_id, 'message_id': message_id,
		 'random_id': random_id, 'message': 'Ищем рандомное слово ' + moon[x%8]})
	locker.acquire()
	word = choice(lottery['word'])
	locker.release()
	local_vk.method('messages.send', {'user_id': user_id, 'random_id': random_id, 'message': "Ваше рандомное слово это...\n" + word})
	locker.acquire()
	ignore.remove(user_id)
	locker.release()

def find(string, tags):
    """ Функция возвращающая True, если в string найдётся tag """
    ret = False
    for tag in tags:
        if string.lower().count(tag) != 0:
            ret = True
    return ret

def write_text(user_id, random_id, message):
	global vk
	return vk.method('messages.send', {'user_id': user_id, 'random_id': random_id, 'message': message})

def send_keyboard(user_id, random_id, message, keyboard):
	global vk
	vk.method('messages.send', {'user_id': user_id, 'random_id': random_id, 'message': message, 'keyboard': keyboard})



keyboards = json.loads(open("keyboards.json", 'r', encoding='utf-8').read())
data = json.loads(open("data.txt", 'r', encoding='utf-8').read())
lottery = json.loads(open("lottery.json", 'r', encoding='utf-8').read())
asking_qustions = list()

keyboard = VkKeyboard(inline=True)
keyboard.add_button("Назад", color=VkKeyboardColor.NEGATIVE)
cancel_keybord = keyboard.get_keyboard()

score = dict()
ignore = list()
locker = Lock()

while True:
	requests = vk.method("messages.getConversations", {"offset": 0, "count": 200, "filter": "unread"})
	for request in requests['items']:
		user_id = request['last_message']['from_id']
		text = request['last_message']['text']
		random_id = request['last_message']['random_id']

		locker.acquire()
		if user_id in ignore:
			locker.release()
			continue
		locker.release()

		if request['last_message'].get('geo'):
			write_text(user_id, random_id, "Ваши коодинаты: ({}, {})".format(
			 	request['last_message']['geo']['coordinates']['latitude'],
				request['last_message']['geo']['coordinates']['longitude']))

		if text == "Начать":
			user_info = vk.method("users.get", {"user_ids": user_id})[0]
			send_keyboard(user_id, random_id, "Приветствую тебя, {}.\n".format(
				user_info['first_name']) + data['spech']['start'], keyboards['start'])
			continue

		if text == "Анализ речи":
			keyboard = VkKeyboard(inline=True)
			keyboard.add_button("Задать вопрос", color=VkKeyboardColor.PRIMARY)
			send_keyboard(user_id, random_id, data['spech']['asking_questions'], keyboard.get_keyboard())
			continue

		if text == "Задать вопрос":
			if user_id not in asking_qustions:
				asking_qustions.append(user_id)
				send_keyboard(user_id, random_id, data['spech']['ready_to_questing'], cancel_keybord)
				continue

		if text == "Рандом":
			locker.acquire()
			if user_id not in score.keys():
				score[user_id] = 3
				s = 3
			else:
				s = score[user_id]
			locker.release()

			if s == 0:
				write_text(user_id, random_id, "Вы снова сможите использовать кнопку рандом только через 30 минут")
				thread_timer = Thread(target=timer, args=(user_id, 30*60))
				locker.acquire()
				score[user_id] = -1
				locker.release()
				thread_timer.start()
				continue

			if s == -1:
				write_text(user_id, random_id, "30 минут ещё не прошли")
				continue

			if s > 0:
				lottary_thread = Thread(target=random_word, args=(user_id, random_id))
				locker.acquire()
				ignore.append(user_id)
				score[user_id] -= 1
				locker.release()
				lottary_thread.start()
				continue

		if user_id in asking_qustions:

			if text.lower() == "назад":
				asking_qustions.remove(user_id)
				send_keyboard(user_id, random_id, "Продолжим", keyboards['start'])
				continue


			done = False
			for question in data['questions']:
				if find(text, question['tags']):
					write_text(user_id, random_id, question['answer'])
					done = True
					break

			if find(text, data['okey']):
				asking_qustions.remove(user_id)
				send_keyboard(user_id, random_id, "Продолжим", keyboards['start'])
				done = True
				continue

			if done == False:
				send_keyboard(user_id, random_id, data['spech']['i_dont_know'], cancel_keybord)
				continue

		if text == "Кнопки в сообщениях":
			send_keyboard(user_id, random_id, data['spech']['inline_example'], keyboards['inline_example'])
			continue


	t.sleep(1)
