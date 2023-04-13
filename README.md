# otf-photo-service
Automation for processing photos

call example
```
curl -X POST -H "Content-Type: application/json" -d '{"awayTeam": "atlanta-hawks", "homeTeam": "los-angeles-clippers", "awayScore": 55, "homeScore": 63, "period": "END 3"}' http://localhost:8080/api/generate
```