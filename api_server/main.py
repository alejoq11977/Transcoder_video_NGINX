import uuid
import os
import asyncio
from fastapi import FastAPI, File, UploadFile, BackgroundTasks
from fastapi.responses import JSONResponse, StreamingResponse
import grpc
import copy

from proto import transcoder_pb2
from proto import transcoder_pb2_grpc

app = FastAPI()
WORKER_ADDRESS = "worker-node:50051"
jobs = {}

def process_video_blocking(job_id, input_path, output_path, resolution):
    try:
        print(f"[API Server - Job {job_id}] Hilo de gRPC: Intentando conectar con worker para {resolution}...")
        with grpc.insecure_channel(WORKER_ADDRESS) as channel:
            stub = transcoder_pb2_grpc.TranscoderServiceStub(channel)
            request = transcoder_pb2.VideoTaskRequest(
                job_id=job_id,
                input_file_path=input_path,
                output_file_path=output_path,
                resolution=resolution
            )
            response = stub.ProcessVideo(request, timeout=30)
            print(f"[API Server - Job {job_id}] Hilo de gRPC: Llamada completada para {resolution}.")
            return response
    except Exception as e:
        print(f"!!! ERROR en el hilo gRPC para Job ID {job_id} ({resolution}): {e}")
        return e

async def run_transcoding_task_async(job_id: str, task_id: str, input_path: str, output_path: str, resolution: str):
    print(f"[API Server - Job {job_id}] Tarea de fondo iniciada para {resolution}.")
    jobs[job_id]["tasks"][task_id]["status"] = "processing"
    loop = asyncio.get_running_loop()
    response = await loop.run_in_executor(
        None, process_video_blocking, job_id, input_path, output_path, resolution
    )
    if isinstance(response, transcoder_pb2.TaskStatusResponse) and response.success:
        jobs[job_id]["tasks"][task_id]["status"] = "completed"
        jobs[job_id]["tasks"][task_id]["download_url"] = f"/downloads/{job_id}/{os.path.basename(output_path)}"
    else:
        jobs[job_id]["tasks"][task_id]["status"] = "failed"
        jobs[job_id]["tasks"][task_id]["error"] = str(response)

@app.post("/upload")
async def upload_video(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    job_id = str(uuid.uuid4())
    upload_dir = f"/media/uploads/{job_id}"
    processed_dir = f"/media/processed/{job_id}"
    os.makedirs(upload_dir, exist_ok=True)
    input_path = os.path.join(upload_dir, file.filename)
    with open(input_path, "wb") as buffer:
        buffer.write(await file.read())
    tasks_to_run = {"480p": "854x480", "720p": "1280x720"}
    jobs[job_id] = {"job_id": job_id, "original_filename": file.filename, "tasks": {}}
    for task_name, resolution in tasks_to_run.items():
        task_id = str(uuid.uuid4())
        output_filename = f"{os.path.splitext(file.filename)[0]}_{task_name}.mp4"
        output_path = os.path.join(processed_dir, output_filename)
        jobs[job_id]["tasks"][task_id] = {"task_id": task_id, "name": task_name, "status": "pending"}
        background_tasks.add_task(run_transcoding_task_async, job_id, task_id, input_path, output_path, resolution)
    return JSONResponse(content={"job_id": job_id})

async def status_generator(job_id: str):
    last_state = None
    initial_sent = False
    while True:
        if job_id in jobs:
            current_state = copy.deepcopy(jobs[job_id])
            if current_state != last_state or not initial_sent:
                yield f"data: {JSONResponse(content=current_state).body.decode('utf-8')}\n\n"
                last_state = current_state
                initial_sent = True
            all_done = all(task["status"] in ["completed", "failed"] for task in current_state["tasks"].values())
            if all_done and len(current_state["tasks"]) > 0:
                break
        else:
            error_state = {"error": "Job ID no encontrado"}
            yield f"data: {JSONResponse(content=error_state).body.decode('utf-8')}\n\n"
            break
        await asyncio.sleep(1)

@app.get("/status/{job_id}")
async def get_job_status(job_id: str):
    return StreamingResponse(status_generator(job_id), media_type="text/event-stream")
