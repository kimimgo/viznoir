# viznoir-intro

Remotion (React) 기반 viznoir 소개 영상 프로젝트.

## 구조

```
src/
  index.ts          # registerRoot entry point
  Root.tsx           # Composition 정의 (55초 @ 30fps, 1920x1080)
  ViznoirIntro.tsx # 5개 장면 시퀀스 오케스트레이션
  styles.ts          # 공통 색상, 폰트, 스타일
  scenes/
    SceneProblem.tsx   # 0-5초: GUI가 느리다 (ParaView mock + red X)
    SceneSolution.tsx  # 5-12초: viznoir 소개 + pip install 타이핑
    SceneDemo.tsx      # 12-30초: AI 대화 시뮬레이션 + 쇼케이스 갤러리
    SceneFeatures.tsx  # 30-45초: 수치 카운트업 + 클라이언트 배지
    SceneCTA.tsx       # 45-55초: install 명령 + GitHub + MIT License
public/showcase/       # 쇼케이스 이미지 (www/에서 복사)
```

## 명령어

```bash
# Remotion Studio (브라우저에서 실시간 편집)
npm run studio

# MP4 렌더링 (out/viznoir-intro.mp4)
npm run build

# GIF 렌더링
npm run render:gif
```

## 디자인

- 색상: 다크 (#0f172a), 파랑 (#3b82f6), 그린 (#10b981)
- 폰트: Inter (sans), JetBrains Mono (code)
- 1920x1080, 30fps, 55초
