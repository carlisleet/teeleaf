FROM python:3.7

RUN apt-get update 
RUN apt-get install -y cron vim curl

#download and install chrome
RUN wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
RUN dpkg -i google-chrome-stable_current_amd64.deb; apt-get -fy install

#install python dependencies
COPY requirements.txt requirements.txt 
RUN pip install -r ./requirements.txt 

# setting enviroment vars
ENV APP_HOME /app 
ENV PORT 1912

# Exposing port 5000 for network access
EXPOSE 1912

#set workspace
WORKDIR ${APP_HOME}

#copy local files
COPY . . 

# running commands for the startup of a container.
CMD exec gunicorn --bind :${PORT} --workers 1 --threads 8 wsgi:web


