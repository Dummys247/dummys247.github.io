class NeuralLink {
    constructor() {
        this.localVideo = document.getElementById('localVideo');
        this.remoteVideo = document.getElementById('remoteVideo');
        this.localCanvas = document.getElementById('localCanvas');
        this.remoteCanvas = document.getElementById('remoteCanvas');
        this.logContainer = document.getElementById('statusLog');
        
        this.localStream = null;
        this.peerConnection = null;
        this.metricsChannel = null;
        this.userId = 'USER-' + Math.floor(Math.random() * 1000000); // Temporary ID
        document.getElementById('local-id').innerText = this.userId;
        
        this.signalingUrl = '/api/neural/signal';
        this.pollingInterval = null;
        this.isNeuralActive = false;
        
        this.models = {
            cocoSsd: null,
            blazeFace: null
        };

        this.rtcConfig = {
            iceServers: [
                { urls: 'stun:stun.l.google.com:19302' }
            ]
        };
        
        this.currentPeerId = null;

        this.init();
    }

    async init() {
        this.log('Initializing Neural Link System...', 'info');
        
        // Event Listeners
        document.getElementById('startBtn').addEventListener('click', () => this.startCamera());
        document.getElementById('refreshPeersBtn').addEventListener('click', () => this.fetchPeers());
        document.getElementById('neuralBtn').addEventListener('click', () => this.toggleNeural());
        
        // Start Polling for Signals
        this.startSignaling();
        
        // Load AI Models
        this.loadModels();
        
        // Hardware & connectivity diagnostics
        this.checkHardware();
        
        // Initial peers fetch
        this.fetchPeers();
    }

    log(msg, type = 'info') {
        const div = document.createElement('div');
        div.className = `log-entry log-${type}`;
        div.innerText = `[${new Date().toLocaleTimeString()}] ${msg}`;
        this.logContainer.appendChild(div);
        this.logContainer.scrollTop = this.logContainer.scrollHeight;
    }

    async startCamera() {
        try {
            this.localStream = await navigator.mediaDevices.getUserMedia({
                video: {
                    width: { ideal: 1280 },
                    height: { ideal: 720 },
                    frameRate: { ideal: 30, max: 30 }
                },
                audio: true
            });
            this.localVideo.srcObject = this.localStream;
            this.log('Camera started successfully', 'success');
            document.getElementById('startBtn').disabled = true;
            document.getElementById('neuralBtn').disabled = false;
        } catch (err) {
            this.log('Error accessing camera: ' + err.message, 'error');
        }
    }

    async checkHardware() {
        try {
            const devices = await navigator.mediaDevices.enumerateDevices();
            const cams = devices.filter(d => d.kind === 'videoinput');
            const status = document.getElementById('connection-status');
            if (cams.length > 0) {
                status.innerText = `CAMERA DETECTED (${cams.length})`;
                status.style.color = '#0f0';
            } else {
                status.innerText = 'NO CAMERA DETECTED';
                status.style.color = '#ff0';
            }
            // Server connectivity
            const resp = await fetch('/health');
            if (resp.ok) {
                this.log('Server reachable', 'success');
            } else {
                this.log('Server health endpoint failed', 'error');
            }
        } catch (e) {
            this.log('Hardware check error: ' + e.message, 'error');
        }
    }
    async loadModels() {
        this.log('Loading Neural Models...', 'warn');
        try {
            // Load models if libraries are available
            if (typeof cocoSsd !== 'undefined' && typeof blazeface !== 'undefined') {
                const [coco, face] = await Promise.all([
                    cocoSsd.load(),
                    blazeface.load()
                ]);
                this.models.cocoSsd = coco;
                this.models.blazeFace = face;
                this.log('Neural Models Loaded (COCO-SSD & BlazeFace)', 'success');
            } else {
                 this.log('TensorFlow.js libraries not loaded. Neural features disabled.', 'error');
            }
        } catch (err) {
            this.log('Failed to load models: ' + err.message, 'error');
        }
    }

    toggleNeural() {
        this.isNeuralActive = !this.isNeuralActive;
        const btn = document.getElementById('neuralBtn');
        if (this.isNeuralActive) {
            btn.innerHTML = '<i class="fas fa-stop"></i> Stop Neural AI';
            btn.style.borderColor = '#0f0';
            this.runInferenceLoop();
        } else {
            btn.innerHTML = '<i class="fas fa-microchip"></i> Start Neural AI';
            btn.style.borderColor = '#ff0000';
            // Clear canvases
            const ctx1 = this.localCanvas.getContext('2d');
            const ctx2 = this.remoteCanvas.getContext('2d');
            ctx1.clearRect(0, 0, this.localCanvas.width, this.localCanvas.height);
            ctx2.clearRect(0, 0, this.remoteCanvas.width, this.remoteCanvas.height);
        }
    }

    async runInferenceLoop() {
        if (!this.isNeuralActive || !this.localVideo.readyState === 4) {
            if (this.isNeuralActive) requestAnimationFrame(() => this.runInferenceLoop());
            return;
        }

        // Process Local Video
        await this.processVideo(this.localVideo, this.localCanvas);

        // Process Remote Video (if connected)
        if (this.remoteVideo.srcObject) {
            await this.processVideo(this.remoteVideo, this.remoteCanvas);
        }

        if (this.isNeuralActive) {
            requestAnimationFrame(() => this.runInferenceLoop());
        }
    }

    async processVideo(video, canvas) {
        if (video.readyState !== 4) return;

        const ctx = canvas.getContext('2d');
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        ctx.clearRect(0, 0, canvas.width, canvas.height);

        // Object Detection
        if (this.models.cocoSsd) {
            const predictions = await this.models.cocoSsd.detect(video);
            predictions.forEach(prediction => {
                ctx.beginPath();
                ctx.rect(...prediction.bbox);
                ctx.lineWidth = 2;
                ctx.strokeStyle = '#00ff00';
                ctx.fillStyle = '#00ff00';
                ctx.stroke();
                ctx.fillText(
                    `${prediction.class} (${Math.round(prediction.score * 100)}%)`,
                    prediction.bbox[0],
                    prediction.bbox[1] > 10 ? prediction.bbox[1] - 5 : 10
                );
            });
        }

        // Face Detection
        if (this.models.blazeFace) {
            const predictions = await this.models.blazeFace.estimateFaces(video, false);
            predictions.forEach(prediction => {
                const start = prediction.topLeft;
                const end = prediction.bottomRight;
                const size = [end[0] - start[0], end[1] - start[1]];
                
                ctx.beginPath();
                ctx.rect(start[0], start[1], size[0], size[1]);
                ctx.lineWidth = 2;
                ctx.strokeStyle = '#ff0000';
                ctx.stroke();
            });
        }
    }

    // --- SIGNALING & PEERS ---

    async fetchPeers() {
        try {
            const response = await fetch('/api/neural/peers');
            const data = await response.json();
            const list = document.getElementById('peers-list');
            list.innerHTML = '';
            
            data.peers.forEach(peerId => {
                // Filter out self if ID matches (though using random IDs now, DB IDs might be different)
                // For this demo, just list all
                const li = document.createElement('li');
                li.innerHTML = `
                    <span><i class="fas fa-user"></i> ${peerId}</span>
                    <button class="btn-connect" onclick="window.neuralLink.connectToPeer('${peerId}')">Connect</button>
                `;
                list.appendChild(li);
            });
            this.log('Peers list updated', 'info');
        } catch (err) {
            this.log('Error fetching peers: ' + err.message, 'error');
        }
    }

    startSignaling() {
        this.pollingInterval = setInterval(async () => {
            try {
                const response = await fetch('/api/neural/signal/poll', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ user_id: this.userId })
                });
                const data = await response.json();
                
                if (data.messages && data.messages.length > 0) {
                    data.messages.forEach(msg => this.handleSignal(msg));
                }
            } catch (err) {
                console.error('Signaling poll error:', err);
            }
        }, 2000); // Poll every 2 seconds
    }

    async handleSignal(signal) {
        const { sender_id, message } = signal;
        this.log(`Received signal from ${sender_id}: ${message.type || 'candidate'}`, 'info');

        if (!this.peerConnection) {
            this.createPeerConnection(sender_id);
        }

        try {
            if (message.type === 'offer') {
                await this.peerConnection.setRemoteDescription(new RTCSessionDescription(message));
                const answer = await this.peerConnection.createAnswer();
                await this.peerConnection.setLocalDescription(answer);
                this.sendSignal(sender_id, answer);
            } else if (message.type === 'answer') {
                await this.peerConnection.setRemoteDescription(new RTCSessionDescription(message));
            } else if (message.candidate) {
                await this.peerConnection.addIceCandidate(new RTCIceCandidate(message));
            }
        } catch (err) {
            this.log('Error handling signal: ' + err.message, 'error');
        }
    }

    async sendSignal(recipientId, message) {
        try {
            await fetch('/api/neural/signal/send', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    sender_id: this.userId,
                    recipient_id: recipientId,
                    message: message
                })
            });
        } catch (err) {
            this.log('Error sending signal: ' + err.message, 'error');
        }
    }

    // --- WEBRTC ---

    createPeerConnection(peerId) {
        this.currentPeerId = peerId;
        this.peerConnection = new RTCPeerConnection(this.rtcConfig);

        // Add local tracks
        this.localStream.getTracks().forEach(track => {
            this.peerConnection.addTrack(track, this.localStream);
        });

        // DataChannel for metrics (only create on offerer side)
        if (!this.metricsChannel) {
            try {
                this.metricsChannel = this.peerConnection.createDataChannel('metrics');
                this.setupMetricsChannel(this.metricsChannel);
            } catch (e) {
                this.log('DataChannel error: ' + e.message, 'error');
            }
        }

        // Handle remote tracks
        this.peerConnection.ontrack = (event) => {
            this.remoteVideo.srcObject = event.streams[0];
            this.log('Remote stream received!', 'success');
        };

        // ICE Candidates
        this.peerConnection.onicecandidate = (event) => {
            if (event.candidate) {
                this.sendSignal(peerId, event.candidate);
            }
        };
        
        this.peerConnection.onconnectionstatechange = () => {
             this.log(`Connection state: ${this.peerConnection.connectionState}`, 'info');
             if (this.peerConnection.connectionState === 'connected') {
                 this.startMetricsLoop();
             }
        };

        // Answerer: receive DataChannel
        this.peerConnection.ondatachannel = (event) => {
            if (event.channel && event.channel.label === 'metrics') {
                this.metricsChannel = event.channel;
                this.setupMetricsChannel(this.metricsChannel);
            }
        };
    }

    async connectToPeer(peerId) {
        this.log(`Initiating connection to ${peerId}...`, 'info');
        this.createPeerConnection(peerId);

        try {
            const offer = await this.peerConnection.createOffer();
            await this.peerConnection.setLocalDescription(offer);
            this.sendSignal(peerId, offer);
        } catch (err) {
            this.log('Error creating offer: ' + err.message, 'error');
        }
    }

    setupMetricsChannel(channel) {
        channel.onopen = () => {
            this.log('Metrics channel open', 'success');
            // Start pinging
            this.pingInterval = setInterval(() => {
                const now = Date.now();
                try {
                    channel.send(JSON.stringify({ type: 'ping', t: now }));
                } catch (e) {
                    // ignore
                }
            }, 3000);
        };
        channel.onmessage = (ev) => {
            try {
                const msg = JSON.parse(ev.data);
                if (msg.type === 'ping') {
                    // Echo with same timestamp
                    channel.send(JSON.stringify({ type: 'pong', t: msg.t }));
                } else if (msg.type === 'pong') {
                    const rtt = Date.now() - msg.t;
                    const el = document.getElementById('conn-latency');
                    if (el) el.innerText = `${rtt} ms`;
                }
            } catch {
                // ignore
            }
        };
        channel.onclose = () => {
            if (this.pingInterval) clearInterval(this.pingInterval);
        };
    }

    async startMetricsLoop() {
        // FPS measurement
        let frames = 0;
        let lastTime = performance.now();
        const fpsEl = document.getElementById('conn-fps');
        const bitrateEl = document.getElementById('conn-bitrate');
        const dtlsEl = document.getElementById('conn-dtls');

        const countFrame = () => {
            frames++;
            requestAnimationFrame(countFrame);
        };
        requestAnimationFrame(countFrame);

        setInterval(async () => {
            const now = performance.now();
            const seconds = (now - lastTime) / 1000;
            const fps = Math.round(frames / seconds);
            frames = 0;
            lastTime = now;
            if (fpsEl) fpsEl.innerText = String(fps);

            // WebRTC stats for bitrate and DTLS
            if (this.peerConnection) {
                try {
                    const stats = await this.peerConnection.getStats();
                    let bytesNow = 0;
                    let bytesThen = this._bytesThen || 0;
                    stats.forEach(report => {
                        if (report.type === 'outbound-rtp' && !report.isRemote && report.bytesSent) {
                            bytesNow += report.bytesSent;
                        }
                        if (report.type === 'transport' && report.dtlsState) {
                            if (dtlsEl) dtlsEl.innerText = report.dtlsState;
                        }
                    });
                    const bitrateKbps = Math.round(((bytesNow - bytesThen) * 8) / 1000 / 1); // per second approx
                    this._bytesThen = bytesNow;
                    if (bitrateEl) bitrateEl.innerText = `${bitrateKbps} kbps`;
                } catch (e) {
                    // ignore
                }
            }
        }, 1000);
    }
}

// Global instance for onclick handlers
window.neuralLink = new NeuralLink();
