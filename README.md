# notification-service-local

## Steps to run locally
1. Make sure Docker and k6 is installed
2. Compose the project using the command -  
`docker compose build`
3. Run the project in detached mode using the command -  
`docker compose up -d`
4. Run the test script inside the folder `test-scripts` using the command -   
`k6 run loadtest.js`