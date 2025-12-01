run:
	docker run -it -d --env-file .env --restart=unless-stopped --name ytbot ytbot_image
stop:
	docker stop ytbot
attach:
	docker attach ytbot
dell:
	docker rm ytbot