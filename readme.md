# 연세대 워크스테이션 세줄요약팀

## Description
정부제공 OpenAPI를 사용하여 국회 입법 예고 정보를 가져오고 ChatGPT를 이용하여 정리하여 유저들에게
이메일로 제공하는 프로그램입니다. 

## Installation
`pip install -r requirements.txt`

## Requirment
프로그램을 정상적으로 작동시키기 위해서는 .env 파일과 subscriptions.db 데이터 베이스가 필요합니다.  
  
.env 파일 내에는 아래와 같은 environment 정보들을 기입하여야합니다.  
GOV_API_KEY는 국회 OpenAPI key, OPENAI_API_KEY는 openai사의 api키, 발송자의 EMAIL_ID와 EMAIL_PW가 필요합니다.  

`
GOV_API_KEY=  
OPENAI_API_KEY=  
EMAIL_ID=  
EMAIL_PW=  
`

subscriptions.db는 (구독자 이름, 구독자 이메일 주소)로 이루어져 있어야합니다.  