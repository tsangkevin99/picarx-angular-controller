import { Component, HostListener, OnDestroy } from '@angular/core';
import { CommonModule, DecimalPipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { VideoFeed } from './video-feed';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, FormsModule, VideoFeed, DecimalPipe],
  templateUrl: './app.html',
})
export class App implements OnDestroy {
  piIp = ''; // Enter your Pi IP here dynamically
  controlState = { throttle: 0, steer: 0, rx: 0, ry: 0 };
  private ws?: WebSocket;
  private keysPressed = new Set<string>();
  private gamepadIndex: number | null = null;

  constructor() {
    window.requestAnimationFrame(() => this.gamepadLoop());
  }

  ngOnDestroy() {
    this.disconnectWebSocket();
  }
  onPiIpChange(event: any) {
    this.piIp = event.target.value;
    this.connectWebSocket();
  }

  connectWebSocket() {
    if (!this.piIp) return;
    if (this.ws) this.ws.close();
    this.ws = new WebSocket(`ws://${this.piIp}:8765`);

    this.ws.onopen = () => this.sendControlState();
    this.ws.onclose = () => setTimeout(() => this.connectWebSocket(), 3000);
    this.ws.onerror = (err) => { console.error('WebSocket error:', err); this.ws?.close(); };
  }

  disconnectWebSocket() {
    if (this.ws) { this.ws.close(); this.ws = undefined; }
  }

  onConnectClick() {
    this.connectWebSocket();
  }

  onExitServerClick() {
    this.disconnectWebSocket();
    console.log('WebSocket server exited.');
  }

  @HostListener('window:keydown', ['$event'])
  onKeyDown(event: KeyboardEvent) {
    this.keysPressed.add(event.key.toLowerCase());
    this.updateControlState();
    event.preventDefault();
  }

  @HostListener('window:keyup', ['$event'])
  onKeyUp(event: KeyboardEvent) {
    this.keysPressed.delete(event.key.toLowerCase());
    this.updateControlState();
    event.preventDefault();
  }

  updateControlState() {
    const keys = this.keysPressed;

    // WASD keyboard controls
    this.controlState.throttle = keys.has('w') ? 1 : keys.has('s') ? -1 : 0;
    this.controlState.steer = keys.has('a') ? -1 : keys.has('d') ? 1 : 0;

    this.sendControlState();
  }

  sendControlState() {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(this.controlState));
    }
  }

  // Xbox / gamepad loop
  gamepadLoop() {
    const gamepads = navigator.getGamepads();
    if (gamepads) {
      for (let i = 0; i < gamepads.length; i++) {
        const gp = gamepads[i];
        if (gp) {
          this.gamepadIndex = i;

          // Right stick: control camera / head
          this.controlState.rx = gp.axes[2] ?? 0;
          this.controlState.ry = gp.axes[3] ?? 0;

          // Triggers: throttle
          const rt = gp.buttons[7]?.value ?? 0; // right trigger forward
          const lt = gp.buttons[6]?.value ?? 0; // left trigger backward
          this.controlState.throttle = rt ? rt : lt ? -lt : this.controlState.throttle;

          this.sendControlState();
        }
      }
    }
    window.requestAnimationFrame(() => this.gamepadLoop());
  }
}
