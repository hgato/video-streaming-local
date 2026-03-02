# Video stream local

## Actor client
Client is represented as a browser application.
Client has a single point of entry gate module.

## Gate module
Entry point component: 
- server traefik for MVP
- load balancer for production scalability
- proxies incoming traffic to Web service and API Gateway

API gateway:
- kong for MVL
- makes an authorization check and transfers traffic to API

## Web srvice
Returns user a browser application on request

## Websocket module
Meant to send user notifications in real time

### Websocket-service
Stateless service. Established 2-way connection to clients.
Works via webservice manger service.

### Websocket-manager-service
Serves as a smart processor between internal system and websockets.
Stateless. Stores a map of user_id vs websocket services
so if websocket service is being scaled horizontally, we still know
what service is responsible for what user connection.

### Redis
Contains a map - user_id vs websocket service IP.

## Video service
Works with video objects. Returns user a list of videos, video metadata and used
as a gateway for external calls to video processing pipeline.
Stateless. State is stored in non-SQL database.

## Ingest CLI
Command line entry point that feeds a video into the system.

## Object Storage
An object storage service. For MVP minIO is used. It has several buckets
that are used for different stages of video processing.

## Video processing pipeline
This module is processing video from the injection step to feeding to the end user

### Rename service 
Responsible for renaming the video and sending it into the correct bucket

### Video lifecycle manager
- consumes requests for video preparation
- stores metadata for preparing/ready videos
- notifies user via websocket when video is ready

### Lifecycle database
Stores temporary metadata for preparing/ready videos

### Queue
Enables message transfer between services

### Video encoding service
Encodes whole video. Does this for the whole file to sustain video quality consistency

### Video chunking service
Breaks down the video in chunks for streaming and creates a manifest

