from playwright.async_api import async_playwright

import time
import json
import asyncio
import datetime
# from datetime import datetime, timedelta


async def go_to_browser() -> dict | bool:
    async with async_playwright() as playwright_context_manager:
        def log_request_headers(request):
            headers = {header: request.headers[header] for header in request.headers}
            all_headers['requests'].append({
                'url': request.url,
                'method': request.method,
                'headers': headers
            })

        def log_response_headers(response):
            headers = {header: response.headers[header] for header in response.headers}
            all_headers['responses'].append({
                'url': response.url,
                'status': response.status,
                'headers': headers
            })

        # def save_all_headers_to_file(headers_dict, filename="all_headers.json"):
        #     with open(filename, 'w', encoding='utf-8') as file:
        #         json.dump(headers_dict['requests'][-1]['headers'], file, indent=4, ensure_ascii=False)

        all_headers = {
            'requests': [],
            'responses': []
        }

        browser = await playwright_context_manager.firefox.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        page.on("request", log_request_headers)
        page.on("response", log_response_headers)

        bad_status_count = 0

        response_obj = await page.goto(url='https://www.ozon.ru/', wait_until='load')
        await page.wait_for_timeout(5_000)

        while True:
            if bad_status_count >= 5:
                await page.close()
                await context.close()
                await browser.close()
                await playwright_context_manager.stop()

                print(f'Start page was reload five times and each time was unsuccessful!!!')
                return False

            if response_obj.status != 200:
                bad_status_count += 1
                response_obj = await page.reload(wait_until='load')
                await page.wait_for_timeout(5_000)
            else:
                break

        ok_button = await page.locator('div > button > div:visible', has_text='ОК').all()
        if len(ok_button) > 0:
            await ok_button[0].click()

        # save_all_headers_to_file(all_headers)
        last_headers = all_headers['requests'][-1]['headers']

        await page.close()
        await context.close()
        await browser.close()
        await playwright_context_manager.stop()

        return last_headers


async def open_file_with_headers(path_to_file: str) -> bool | None:
    with open(path_to_file, 'r', encoding='utf-8') as file:
        headers = json.load(file)

    curr_date_time = datetime.datetime.now(datetime.UTC)
    date_from_json = headers['date']

    flag_to_open_browser = False

    if date_from_json:
        date_from_json = datetime.datetime.strptime(date_from_json, "%d.%m.%Y|%H:%M")

        # обновляемся раз в 23 часа и 50 минут
        seconds_between_update = 23 * 60 * 60 + 50 * 60

        if curr_date_time - date_from_json > datetime.timedelta(seconds=seconds_between_update):
            flag_to_open_browser = True
    else:
        flag_to_open_browser = True

    if flag_to_open_browser:
        current_loop = asyncio.get_event_loop()
        new_headers = await current_loop.create_task(go_to_browser())

        if isinstance(new_headers, bool):
            return None

        headers['date'] = curr_date_time.strftime("%d.%m.%Y|%H:%M")
        headers['headers'] = new_headers

        with open(path_to_file, 'w', encoding='utf-8') as file:
            json.dump(headers, file, indent=4, ensure_ascii=False)

        return True

    return False


if __name__ == '__main__':
    while True:
        sleep_sec = 3 * 60 * 60

        # путь можно указать абсолютный для того, чтобы положить json в корень проекта, из которого будет использоваться
        path_to_file_with_headers = 'headers.json'

        print("Run:", (start_time := datetime.datetime.now(datetime.UTC)).strftime('%d.%m.%Y | %H:%M'), '<- UTC time!')
        flag = asyncio.run(open_file_with_headers(path_to_file_with_headers))

        # flag может принимать None в случае, если страница в браузере была перезагружена 5 раз и на каждом запуске
        # мы получали код отличный от 200. В этом случае следующую попытку открытия страницы мы выполним через 3 минуты.
        # flag принимает значение True - если потребовалось открыть браузер и при этом заголовки были успешно получены.
        # flag принимает значение False - если с момента последнего обновления заголовков прошло меньше суток.
        if flag is None:
            sleep_sec = 3 * 60
            message = 'Bad response!'
        else:
            if flag:
                message = 'File was successfully save.'
            else:
                message = 'Headers was reading from file.'

        print(
            f'{message} Next run in {(start_time + datetime.timedelta(seconds=sleep_sec)).strftime("%d.%m.%Y | %H:%M")}'
        )

        time.sleep(sleep_sec)
