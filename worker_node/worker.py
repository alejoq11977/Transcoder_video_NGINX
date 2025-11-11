import grpc
from concurrent import futures
import time
import subprocess
import os

from proto import transcoder_pb2
from proto import transcoder_pb2_grpc

class TranscoderServicer(transcoder_pb2_grpc.TranscoderServiceServicer):
    def ProcessVideo(self, request, context):
        job_id = request.job_id
        input_path = request.input_file_path
        output_path = request.output_file_path
        resolution = request.resolution

        print(f"[Worker] Tarea recibida para Job ID: {job_id}. Convirtiendo a {resolution}...")

        output_dir = os.path.dirname(output_path)
        os.makedirs(output_dir, exist_ok=True)

        ffmpeg_command = [
            'ffmpeg',
            '-y',
            '-i', input_path,
            '-s', resolution,
            '-hide_banner',
            '-loglevel', 'error',
            output_path
        ]

        try:
            result = subprocess.run(ffmpeg_command, check=True, capture_output=True, text=True)
            print(f"[Worker] Éxito para Job ID: {job_id} ({resolution}).")
            return transcoder_pb2.TaskStatusResponse(
                success=True,
                message=f"Conversión a {resolution} completada exitosamente."
            )
        except subprocess.CalledProcessError as e:
            error_message = e.stderr.strip()
            print(f"[Worker] ERROR para Job ID: {job_id} ({resolution}). Error: {error_message}")
            return transcoder_pb2.TaskStatusResponse(
                success=False,
                message=f"FFmpeg falló: {error_message}"
            )

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    transcoder_pb2_grpc.add_TranscoderServiceServicer_to_server(TranscoderServicer(), server)
    port = "50051"
    server.add_insecure_port(f"0.0.0.0:{port}")
    print(f"Servidor Worker iniciado. Escuchando en el puerto {port}...")
    server.start()
    server.wait_for_termination()

if __name__ == '__main__':
    serve()
