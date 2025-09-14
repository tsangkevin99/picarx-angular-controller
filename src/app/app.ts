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
  piIp = ''; // dynamically entered in UI
  controlState = { throttle: 0, steer: 0, rx: 0, ry: 0, button_y : false, button_x: false};
  private ws?: WebSocket;
  private keysPressed = new Set<string>();
  private gamepadIndex: number | null = null;

  constructor() {
    window.requestAnimationFrame(() => this.gamepadLoop());
  }

  ngOnDestroy() {
    this.disconnectWebSocket();
  }

  // Called when input changes
  onPiIpChange(event: any) {
    this.piIp = event.target.value;
  }

  onConnectClick() {
    this.connectWebSocket();
  }

  onExitServerClick() {
    this.disconnectWebSocket();
    console.log('WebSocket disconnected');
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

// Gamepad / Xbox controller loop
gamepadLoop() {
  const gamepads = navigator.getGamepads();
  if (gamepads) {
    for (let i = 0; i < gamepads.length; i++) {
      const gp = gamepads[i];
      if (gp) {
        this.gamepadIndex = i;

        // Left stick for steering
        const lx = gp.axes[0] ?? 0;  // left stick horizontal
        this.controlState.steer = Math.abs(lx) > 0.1 ? lx : 0;  // deadzone

        // Right stick for camera/head
        const rx = gp.axes[2] ?? 0; // right stick horizontal
        const ry = gp.axes[3] ?? 0; // right stick vertical
        this.controlState.rx = Math.abs(rx) > 0.1 ? rx : 0;  // deadzone
        this.controlState.ry = Math.abs(ry) > 0.1 ? ry : 0;

        // Triggers for throttle
        const rt = gp.buttons[7]?.value ?? 0;  // right trigger forward
        const lt = gp.buttons[6]?.value ?? 0;  // left trigger backward
        if (rt > 0.1) this.controlState.throttle = rt;
        else if (lt > 0.1) this.controlState.throttle = -lt;
        else this.controlState.throttle = 0;  // reset if no trigger pressed

        // Buttons for head reset
        this.controlState.button_y = gp.buttons[3]?.pressed ?? false; // Y button
        this.controlState.button_x = gp.buttons[2]?.pressed ?? false; // X button

        // Send updated control state to backend
        this.sendControlState();
      }
    }
  }
  window.requestAnimationFrame(() => this.gamepadLoop());
}


}
