# Lazybot Docker deployment
FROM python:3.5

MAINTAINER Sri Ramanujam

# setting up the python environment first, less likely to change
RUN mkdir /bot
WORKDIR /bot
COPY ./requirements.txt /bot
RUN pip install -r /bot/requirements.txt

# this stuff will change more often
COPY ./plugins /bot/plugins

# If you wish to bake in the config.ini, uncomment this line
ONBUILD COPY ./config.ini /bot

# run the thing
CMD ["irc3", "./config.ini"]
