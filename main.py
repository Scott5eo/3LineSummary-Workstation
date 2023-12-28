#본 프로그램은 2023년 연세대학교 워크스테이션 프로젝트로 작성됨
#Version: 0.0.3
#Author: 서동진
#Description: 정부제공 OpenAPI를 사용하여 국회 의안활동 정보를 가져오고 정리하여 유저들에게
#             제공하는 프로그램이다. 이를 위해 big data를 활용하여 정보의 중요도를 판단하고
#             인공지능 모델을 활용하여 내용을 요약하고, 유저들의 편의를 위해 email 형식으로
#             정보를 제공한다.
import requests
import pandas as pd
from bs4 import BeautifulSoup
from openai import OpenAI
import os
from dotenv import load_dotenv
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import sqlite3

class SMTPClient:
    def __init__(self, sender, pw):
        self.sender = sender
        self.pw = pw

    def send_email(self, subject, body, recipient):
        msg = MIMEMultipart()
        msg['Subject'] = subject
        msg['From'] = self.sender
        msg['To'] = recipient
        msg.attach(MIMEText(body, 'plain'))
        self.server = smtplib.SMTP('smtp.gmail.com', 587)
        self.server.starttls()
        self.server.login(self.sender, self.pw)
        self.server.sendmail(self.sender, recipient, msg.as_string())
        self.server.quit()

#OpenAPI 활용을 위해 API key가 필요합니다. 자세한 내용은 URL 참고: https://open.assembly.go.kr/portal/openapi/openApiDevPage.do, https://openai.com/blog/openai-api
#API key는 환경변수에 저장되어 있어야 합니다. .env 파일을 만들어서 환경변수를 저장하세요. 발송자 이메일 아이디와 비밀번호도 환경변수에 저장되어 있어야 합니다.
#환경 변수 이름: GOV_API_KEY, OPENAI_API_KEY, EMAIL_ID, EMAIL_PW
#이메일을 보내기 위해 subscriptions.db 데이터 베이스가 필요합니다. 데이터 베이스에는 (이름, 이메일) 정보가 저장되어 있어야 합니다.
load_dotenv(verbose=False)
gov_api_key = os.getenv('GOV_API_KEY')
openai_api_key = os.getenv('OPENAI_API_KEY')
conn = sqlite3.connect('subscriptions.db')
c = conn.cursor()
email_id = os.getenv('EMAIL_ID')
email_pw = os.getenv('EMAIL_PW')
smtp_client = SMTPClient(email_id, email_pw)

#---------------------OpenAI---------------------
client = OpenAI(api_key=openai_api_key)

#필수 파라미터
#Key = api_key, Type = json, pIndex = 1, pSize = 100
#입법 예고 목록 조회
url = "https://open.assembly.go.kr/portal/openapi/nknalejkafmvgzmpt"
rqst_type = 'json'
pIndex = 1
pSize = 100 #최대 100개의 데이터를 불러올 수 있음

#send request
response = requests.get(url, params = {"Key": gov_api_key, "Type": rqst_type, "pIndex": pIndex, "pSize": pSize})
response = response.json() #json 형식으로 변환
info_type = 'nknalejkafmvgzmpt' #진행중 입법예고
#---------------------Header---------------------
header = response[info_type][0] #메세지, 결과 코드 등이 담겨있음
header_message = header['head'][1]['RESULT']['MESSAGE']
header_code = header['head'][1]['RESULT']['CODE']
if(header_code != 'INFO-000'):
    print("API 요청에 실패하였습니다. 에러 코드: " + header_code)
print(header_message)

#---------------------Body---------------------
body = response[info_type][1]['row'] #실제 데이터가 담겨있음
#put it into dataframe
body_df = pd.DataFrame.from_dict(body)
#number of rows
print("총 " + str(len(body_df)) + "개의 입법예고를 불러왔습니다. 마감일 순으로 정렬합니다.")

# #sort by end date
# body_df = body_df.sort_values(by=['NOTI_ED_DT'])
#delete entries that its end date is after one week from today
today = pd.Timestamp.today()
end_date = today + pd.Timedelta(days=1)
#change 'noti-ed-dt' column to datetime type with just date
body_df['NOTI_ED_DT'] = pd.to_datetime(body_df['NOTI_ED_DT'])
body_df = body_df[body_df['NOTI_ED_DT'] < end_date]
#reset index
body_df = body_df.reset_index(drop=True)
print("오늘 마감인 입법 예고는 총 " + str(len(body_df[body_df['NOTI_ED_DT'] < end_date])) + "개 입니다.\n")

#---------------------Data---------------------
for i in range(len(body_df)):
    row = body_df.iloc[i]
    title = row['BILL_NAME']
    link_url = row['LINK_URL']
    end_date = row['NOTI_ED_DT']
    # print(f"제목: {row['BILL_NAME']}")
    # print(f"링크: {link_url}")
    # print(f"마감일: {end_date}")

    #--------------------get information------------------
    rsp = requests.get(link_url)
    soup = BeautifulSoup(rsp.content, 'html.parser')

    #제안이유 및 주요내용
    content = soup.find('div', {'class': 'desc'})
    #pretty print and remove <br/> and <div> tags
    content = content.prettify()
    content = content.replace("<br/>", "")
    content = content.replace("<div class=\"desc\">", "")
    content = content.replace("</div>", "")
    # print(content)
    #save content to body_df
    body_df.at[i, 'content'] = content
    
    #--------------------summarize------------------
    prompt = f"{title}\n{content}"
    response = client.chat.completions.create(
        messages = [
            {"role":"system", "content":"귀하는 국회 입법예고 정보를 알기 쉽게 요약하여 제공하는 비서임. 주어지는 내용을 중립적으로 약어, 줄임말로 3줄 불릿포인트(1,2,3)로 요약함. 그리고 법 관련 키워드 3개 추출함 (예시: '키워드: 교육, 안전, 주택')."},
            {"role":"user", "content":prompt}
        ],
        model='gpt-3.5-turbo'
    )
    summary = response.choices[0].message.content
    body_df.at[i, 'summary'] = summary

    if i == 5: break #manual break to save time and openai api calls(money)

c.execute("SELECT * FROM subscriptions")
subscribers = c.fetchall()
cnt = 0
for subscriber in subscribers:
    name = subscriber[0]
    email_body = f"안녕하세요 {name}님,\n오늘의 마감 입법예고 세줄요약입니다.\n"
    tmp = ""
    for i in range(5):
        tmp = tmp + "\n입법 제목: " + body_df.iloc[i]['BILL_NAME'] + "\n"
        tmp = tmp + "마감일: " + str(body_df.iloc[i]['NOTI_ED_DT'].date()) + "\n"
        tmp = tmp + "링크: " + body_df.iloc[i]['LINK_URL'] + "\n"
        tmp = tmp + "요약:\n" + body_df.iloc[i]['summary'] + "\n"
    email_body = email_body + tmp
    email_body = email_body + "\n\n밝은 미래를 위해,\n세줄요약 서비스 드림\n"
    
    smtp_client.send_email(f"{str(today.date())}일, 오늘의 입법예고 세줄요약", email_body, subscriber[1])
    cnt = cnt + 1
print(f"{cnt}명에게 이메일을 보냈습니다.")
print(f"마지막 이메일 내용:")
print(email_body)
c.close()