import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-video-feed',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './video-feed.html',
  styleUrls: ['./video-feed.css']
})
export class VideoFeed {
  @Input() piIp: string = '';

  get mjpgUrl(): string {
    // Use the Flask endpoint served by your Python server
    // Don’t build the URL when piIp is empty to avoid broken requests
    return this.piIp ? `http://${this.piIp}:9000/video_feed` : '';
  }

  onError() {
    console.error('Failed to load video stream from Pi.');
  }
}
