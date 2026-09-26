export interface Word {
  word: string;
  start: number;
  end: number;
}

export interface GroundTruth {
  text: string;
  segments: any[];
  words: Word[];
}

export interface SongMeta {
  name: string;
  audio: string;
  words: number;
  duration: number;
  youtube_url: string;
}
