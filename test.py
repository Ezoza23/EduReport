import requests

response = requests.post(
    "https://ciu.edupage.org/timetable/server/regulartt.js?__func=regularttGetData",
    json={"__args": [None, "13"], "__gsh": "00000000"},
)

print(response.status_code)