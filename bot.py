import os
import json
import logging
import requests
import time
import random
import asyncio
from datetime import datetime
from pathlib import Path
from colorama import init, Fore
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Initialize colorama
init(autoreset=True)

class Config:
    def __init__(self, auto_task, auto_game, min_points, max_points, interval_minutes):
        self.auto_task = auto_task
        self.auto_game = auto_game
        self.min_points = min_points
        self.max_points = max_points
        self.interval_minutes = interval_minutes

class Binance:
    def __init__(self, account_index, query_string, config: Config, proxy=None):
        self.account_index = account_index
        self.query_string = query_string
        self.proxy = proxy
        self.proxy_ip = "Unknown" if proxy else "Direct"
        self.headers = {
            "Accept": "*/*",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "vi-VN,vi;q=0.9,fr-FR;q=0.8,fr;q=0.7,en-US;q=0.6,en;q=0.5",
            "Content-Type": "application/json",
            "Origin": "https://www.binance.com",
            "Referer": "https://www.binance.com/vi/game/tg/moon-bix",
            "Sec-Ch-Ua": '"Not/A)Brand";v="99", "Google Chrome";v="115", "Chromium";v="115"',
            "Sec-Ch-Ua-Mobile": "?1",
            "Sec-Ch-Ua-Platform": '"Android"',
            "User-Agent": self.get_random_android_user_agent()
        }
        self.game_response = None
        self.game = None
        self.config = config
        logging.basicConfig(level=logging.INFO)

    @staticmethod
    def get_random_android_user_agent():
        android_user_agents = [
            "Mozilla/5.0 (Linux; Android 10; SM-G975F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.120 Mobile Safari/537.36",
            "Mozilla/5.0 (Linux; Android 11; Pixel 4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.159 Mobile Safari/537.36",
            "Mozilla/5.0 (Linux; Android 12; SM-G998B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.62 Mobile Safari/537.36",
            "Mozilla/5.0 (Linux; Android 11; OnePlus 9 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.164 Mobile Safari/537.36",
            "Mozilla/5.0 (Linux; Android 10; Redmi Note 9 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.131 Mobile Safari/537.36"
        ]
        return random.choice(android_user_agents)

    def log(self, msg, type='info'):
        timestamp = datetime.now().strftime('%H:%M:%S')
        account_prefix = f"[Pemulung {self.account_index + 1}]"
        ip_prefix = f"[{self.proxy_ip}]"
        log_message = {
            'success': f"{account_prefix}{ip_prefix} {Fore.GREEN}{msg}",
            'error': f"{account_prefix}{ip_prefix} {Fore.RED}{msg}",
            'warning': f"{account_prefix}{ip_prefix} {Fore.YELLOW}{msg}",
            'custom': f"{account_prefix}{ip_prefix} {Fore.MAGENTA}{msg}"
        }.get(type, f"{account_prefix}{ip_prefix} {msg}")
        
        print(f"[{timestamp}] {log_message}")

    def create_requests_session(self):
        session = requests.Session()
        if self.proxy:
            proxy = {"http": self.proxy, "https": self.proxy}
            session.proxies.update(proxy)
        retry = Retry(connect=3, backoff_factor=0.5)
        adapter = HTTPAdapter(max_retries=retry)
        session.mount('http://', adapter)
        session.mount('https://', adapter)
        session.headers.update(self.headers)
        return session

    def check_proxy_ip(self):
        try:
            session = self.create_requests_session()
            response = session.get('https://api.ipify.org?format=json')
            if response.status_code == 200:
                self.proxy_ip = response.json().get('ip')
            else:
                raise ValueError(f"Cannot check proxy IP. Status code: {response.status_code}")
        except Exception as e:
            raise ValueError(f"Error checking proxy IP: {str(e)}")

    def call_binance_api(self, query_string):
        access_token_url = "https://www.binance.com/bapi/growth/v1/friendly/growth-paas/third-party/access/accessToken"
        user_info_url = "https://www.binance.com/bapi/growth/v1/friendly/growth-paas/mini-app-activity/third-party/user/user-info"
        
        session = self.create_requests_session()
        
        try:
            response = session.post(access_token_url, json={"queryString": query_string, "socialType": "telegram"})
            access_token_response = response.json()
            if access_token_response.get('code') != "000000" or not access_token_response.get('success'):
                raise ValueError(f"Failed to get access token: {access_token_response.get('message')}")
            
            access_token = access_token_response.get('data', {}).get('accessToken')
            session.headers.update({"X-Growth-Token": access_token})
            
            response = session.post(user_info_url, json={"resourceId": 2056})
            user_info_response = response.json()
            if user_info_response.get('code') != "000000" or not user_info_response.get('success'):
                raise ValueError(f"Failed to get user info: {user_info_response.get('message')}")
            
            return {"userInfo": user_info_response.get('data'), "accessToken": access_token}
        except Exception as e:
            self.log(f"API call failed: {str(e)}", 'error')
            return None
    
    def start_game(self, access_token):
        try:
            response = self.create_requests_session().post(
                'https://www.binance.com/bapi/growth/v1/friendly/growth-paas/mini-app-activity/third-party/game/start',
                json={"resourceId": 2056},
                headers={"X-Growth-Token": access_token}
            )

            self.game_response = response.json()
            if self.game_response.get('code') == '000000':
                self.log("Started Game", 'success')
                return True

            if self.game_response.get('code') == '116002':
                self.log("Not enough to play!", 'warning')
            else:
                self.log("Error starting game!", 'error')
            return False
        except Exception as e:
            self.log(f"Cannot start game: {str(e)}", 'error')
            return False

    async def game_data(self):
        try:
            response = self.create_requests_session().post('https://vemid42929.pythonanywhere.com/api/v1/moonbix/play', json=self.game_response)

            if response.json().get('message') == 'success':
                self.game = response.json().get('game')
                self.log("Received game data", 'success')
                return True

            self.log(response.json().get('message'), 'warning')
            return False
        except Exception as e:
            self.log(f"Error receiving game data: {str(e)}", 'error')
            return False

    async def complete_game(self, access_token):
        try:
            response = self.create_requests_session().post(
                'https://www.binance.com/bapi/growth/v1/friendly/growth-paas/mini-app-activity/third-party/game/complete',
                json={
                    "resourceId": 2056, 
                    "payload": self.game.get('payload'), 
                    "log": self.game.get('log')
                },
                headers={"X-Growth-Token": access_token}
            )

            if response.json().get('code') == '000000' and response.json().get('success'):
                self.log(f"Completed game | Received {self.game.get('log')} points", 'custom')
                return True

            self.log(f"Cannot complete game: {response.json().get('message')}", 'error')
            return False
        except Exception as e:
            self.log(f"Error completing game: {str(e)}", 'error')
            return False

    async def get_task_list(self, access_token):
        try:
            response = self.create_requests_session().post(
                "https://www.binance.com/bapi/growth/v1/friendly/growth-paas/mini-app-activity/third-party/task/list",
                json={"resourceId": 2056},
                headers={"X-Growth-Token": access_token}
            )

            if response.json().get('code') != "000000" or not response.json().get('success'):
                raise ValueError(f"Cannot get task list: {response.json().get('message')}")

            task_list = response.json().get('data', {}).get('data')[0].get('taskList', {}).get('data')
            return [task.get('resourceId') for task in task_list if task.get('completedCount') == 0]
        except Exception as e:
            self.log(f"Cannot get task list: {str(e)}", 'error')
            return None

    async def complete_task(self, access_token, resource_id):
        try:
            response = self.create_requests_session().post(
                "https://www.binance.com/bapi/growth/v1/friendly/growth-paas/mini-app-activity/third-party/task/complete",
                json={"resourceIdList": [resource_id], "referralCode": None},
                headers={"X-Growth-Token": access_token}
            )

            if response.json().get('code') != "000000" or not response.json().get('success'):
                raise ValueError(f"Cannot complete task: {response.json().get('message')}")

            if response.json().get('data', {}).get('type'):
                self.log(f"Task {response.json().get('data').get('type')} completed!", 'success')

            return True
        except Exception as e:
            self.log(f"Cannot complete task: {str(e)}", 'error')
            return False

    async def complete_tasks(self, access_token):
        resource_ids = await self.get_task_list(access_token)
        if not resource_ids or len(resource_ids) == 0:
            self.log("No incomplete tasks", 'info')
            return

        for resource_id in resource_ids:
            if resource_id != 2058:
                if await self.complete_task(access_token, resource_id):
                    self.log(f"Completed task: {resource_id}", 'success')
                else:
                    self.log(f"Cannot complete task: {resource_id}", 'warning')
                time.sleep(1)

    async def play_game_if_tickets_available(self):
        try:
            if self.proxy:
                self.check_proxy_ip()
        except Exception as e:
            self.log(f"Cannot check proxy IP: {str(e)}", 'error')
            return

        result = self.call_binance_api(self.query_string)
        if not result:
            return

        user_info = result.get('userInfo')
        access_token = result.get('accessToken')
        total_grade = user_info.get('metaInfo', {}).get('totalGrade')
        available_tickets = user_info.get('metaInfo', {}).get('totalAttempts') - user_info.get('metaInfo', {}).get('consumedAttempts')

        self.log(f"Total points: {total_grade}")
        self.log(f"Tickets available: {available_tickets}")
        
        if self.config.auto_task:
            await self.complete_tasks(access_token)

        if self.config.auto_game:
            while available_tickets > 0:
                self.log(f"Starting game with {available_tickets} tickets available", 'info')
                if await self.start_game(access_token):
                    if await self.game_data():
                        await asyncio.sleep(50)
                        points = random.randint(self.config.min_points, self.config.max_points)
                        if await self.complete_game(access_token):
                            available_tickets -= 1
                            self.log(f"Tickets remaining: {available_tickets}", 'info')
                            await asyncio.sleep(3)
                        else:
                            break
                    else:
                        self.log("Cannot receive game data", 'error')
                        break
                else:
                    self.log("Cannot start game", 'error')
                    break

            if available_tickets == 0:
                self.log("No more tickets available", 'success')


async def run_worker(account_index, query_string, proxy, config):
    client = Binance(account_index, query_string, config, proxy)
    await client.play_game_if_tickets_available()


async def main():
    data_file = Path(__file__).parent / 'data.txt'
    proxy_file = Path(__file__).parent / 'proxy.txt'
    config_file = Path(__file__).parent / 'config.json'

    # Ensure config file exists
    if not config_file.exists():
        with open(config_file, 'w') as f:
            json.dump({
                "auto_task": True,
                "auto_game": True,
                "min_points": 100,
                "max_points": 300,
                "interval_minutes": 60
            }, f, indent=4)

    with open(data_file, 'r') as file:
        data = file.read().replace('\r', '').split('\n')

    with open(proxy_file, 'r') as file:
        proxies = file.read().split('\n')

    with open(config_file, 'r') as file:
        config_data = json.load(file)
        config = Config(
            auto_task=config_data.get("auto_task", True),
            auto_game=config_data.get("auto_game", True),
            min_points=config_data.get("min_points", 100),
            max_points=config_data.get("max_points", 300),
            interval_minutes=config_data.get("interval_minutes", 60)
        )

    data = [line for line in data if line.strip()]
    proxies = [line for line in proxies if line.strip()]

    max_threads = 10
    wait_time = config.interval_minutes * 60  # Convert minutes to seconds

    while True:
        tasks = []
        for i in range(0, len(data)):
            account_index = i
            query_string = data[account_index]
            proxy = proxies[account_index % len(proxies)] if proxies else None
            tasks.append(run_worker(account_index, query_string, proxy, config))

            if len(tasks) >= max_threads or i == len(data) - 1:
                await asyncio.gather(*tasks)
                tasks = []
                await asyncio.sleep(3)

        print(f"All accounts processed. Waiting for {wait_time // 60} minutes before restarting...")
        await asyncio.sleep(wait_time)


if __name__ == '__main__':
    asyncio.run(main())
