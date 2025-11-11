document.addEventListener('DOMContentLoaded', () => {
    const uploadBox = document.getElementById('upload-box');
    const fileInput = document.getElementById('file-input');
    const uploadProgressContainer = document.getElementById('upload-progress-container');
    const uploadProgressBar = document.getElementById('upload-progress-bar');
    const uploadStatus = document.getElementById('upload-status');
    const jobStatusSection = document.getElementById('job-status-section');
    const originalFilenameSpan = document.getElementById('original-filename');
    const jobIdSpan = document.getElementById('job-id-display');
    const tasksContainer = document.getElementById('tasks-container');

    const uploadFile = (file) => {
        const formData = new FormData();
        formData.append('file', file);
        uploadProgressContainer.style.display = 'block';
        uploadStatus.textContent = `Subiendo ${file.name}...`;
        const xhr = new XMLHttpRequest();
        xhr.open('POST', '/upload', true);
        xhr.upload.onprogress = (event) => {
            if (event.lengthComputable) {
                const percentComplete = (event.loaded / event.total) * 100;
                uploadProgressBar.style.width = percentComplete + '%';
            }
        };
        xhr.onload = () => {
            if (xhr.status === 200) {
                uploadProgressBar.style.width = '100%';
                uploadStatus.textContent = '¡Subida completada! Procesando...';
                const response = JSON.parse(xhr.responseText);
                startListeningForStatus(response.job_id, file.name);
            } else {
                uploadStatus.textContent = 'Error en la subida.';
                console.error('Server error:', xhr.responseText);
            }
        };
        xhr.onerror = () => {
            uploadStatus.textContent = 'Error de red durante la subida.';
        };
        xhr.send(formData);
    };

    const startListeningForStatus = (jobId, originalFilename) => {
        jobStatusSection.style.display = 'block';
        originalFilenameSpan.textContent = originalFilename;
        jobIdSpan.textContent = jobId;
        const eventSource = new EventSource(`/status/${jobId}`);
        eventSource.onmessage = (event) => {
            const job = JSON.parse(event.data);
            tasksContainer.innerHTML = '';
            for (const taskId in job.tasks) {
                const task = job.tasks[taskId];
                const taskCard = document.createElement('div');
                taskCard.className = 'task-card';
                let downloadLink = '';
                if (task.status === 'completed' && task.download_url) {
                    downloadLink = `<a href="${task.download_url}" class="download-btn" download>Descargar</a>`;
                }
                taskCard.innerHTML = `
                    <div class="task-info">🎬 ${task.name}</div>
                    <div class="task-status ${task.status}">${task.status.toUpperCase()}</div>
                    ${downloadLink}
                `;
                tasksContainer.appendChild(taskCard);
            }
            const allDone = Object.values(job.tasks).every(t => t.status === 'completed' || t.status === 'failed');
            if (allDone) {
                eventSource.close();
                console.log('Todas las tareas terminadas. Conexión SSE cerrada.');
            }
        };
        eventSource.onerror = (err) => {
            console.error('Error en la conexión SSE:', err);
            eventSource.close();
        };
    };

    uploadBox.addEventListener('click', () => fileInput.click());
    fileInput.addEventListener('change', () => {
        if (fileInput.files.length > 0) {
            uploadFile(fileInput.files[0]);
        }
    });
    uploadBox.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadBox.classList.add('dragover');
    });
    uploadBox.addEventListener('dragleave', () => {
        uploadBox.classList.remove('dragover');
    });
    uploadBox.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadBox.classList.remove('dragover');
        if (e.dataTransfer.files.length > 0) {
            fileInput.files = e.dataTransfer.files;
            uploadFile(fileInput.files[0]);
        }
    });
});
