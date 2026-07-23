const pptxgen = require("pptxgenjs");
const path = require("path");

const pptx = new pptxgen();
pptx.layout = "LAYOUT_WIDE";
pptx.author = "Only My Face";
pptx.subject = "Only My Face 사용 안내";
pptx.title = "Only My Face 사용 방법";
pptx.company = "Only My Face";
pptx.lang = "ko-KR";
pptx.theme = {
  headFontFace: "Arial",
  bodyFontFace: "Arial",
  lang: "ko-KR",
};
pptx.defineLayout({ name: "WIDE", width: 13.333, height: 7.5 });
pptx.layout = "WIDE";

const C = {
  ink: "18212B",
  muted: "5D6978",
  violet: "7B3FF2",
  violetLight: "EEE8FF",
  mint: "29B879",
  paper: "FFFFFF",
  soft: "F6F7FB",
  line: "DFE3EB",
  dark: "1A1630",
};
const SHOT = path.join(__dirname, "01-main-screen.png");
const ICON = path.join(__dirname, "..", "assets", "only-my-face-icon.png");
const SAMPLE = path.join(__dirname, "..", "assets", "sample-face.png");

function addTitle(slide, kicker, title, body) {
  slide.addText(kicker, { x: 0.62, y: 0.48, w: 4.5, h: 0.25, fontFace: "Arial", fontSize: 10, bold: true, color: C.violet, margin: 0, charSpacing: 1.1 });
  slide.addText(title, { x: 0.62, y: 0.81, w: 7.2, h: 0.52, fontFace: "Arial", fontSize: 27, bold: true, color: C.ink, margin: 0, breakLine: false });
  if (body) slide.addText(body, { x: 0.62, y: 1.44, w: 7.8, h: 0.35, fontFace: "Arial", fontSize: 12, color: C.muted, margin: 0 });
}
function addFooter(slide, page) {
  slide.addText("Only My Face · 사진은 내 PC 안에서 처리됩니다", { x: 0.62, y: 7.08, w: 5.6, h: 0.18, fontFace: "Arial", fontSize: 9, color: "7B8592", margin: 0 });
  slide.addText(String(page), { x: 12.12, y: 7.05, w: 0.5, h: 0.2, fontFace: "Arial", fontSize: 10, bold: true, color: C.violet, align: "right", margin: 0 });
}
function card(slide, x, y, w, h, fill = C.paper) {
  slide.addShape(pptx.ShapeType.roundRect, { x, y, w, h, rectRadius: 0.12, fill: { color: fill }, line: { color: C.line, transparency: 40 }, shadow: { type: "outer", color: "718096", opacity: 0.10, blur: 1.5, angle: 45, distance: 1 } });
}
function bubble(slide, n, x, y) {
  slide.addShape(pptx.ShapeType.ellipse, { x, y, w: 0.38, h: 0.38, fill: { color: C.violet }, line: { color: C.violet } });
  slide.addText(String(n), { x, y: y + 0.01, w: 0.38, h: 0.24, fontFace: "Arial", fontSize: 13, bold: true, color: C.paper, align: "center", margin: 0 });
}
function note(slide, n, title, text, x, y, w) {
  bubble(slide, n, x, y);
  slide.addText(title, { x: x + 0.5, y: y - 0.01, w: w - 0.5, h: 0.2, fontFace: "Arial", fontSize: 13, bold: true, color: C.ink, margin: 0 });
  slide.addText(text, { x: x + 0.5, y: y + 0.26, w: w - 0.5, h: 0.5, fontFace: "Arial", fontSize: 10.5, color: C.muted, margin: 0, breakLine: false, fit: "shrink" });
}

// 1. Cover
{
  const slide = pptx.addSlide();
  slide.background = { color: C.dark };
  slide.addShape(pptx.ShapeType.ellipse, { x: 9.9, y: -1.5, w: 4.5, h: 4.5, fill: { color: "382A70", transparency: 10 }, line: { color: "382A70", transparency: 100 } });
  slide.addShape(pptx.ShapeType.ellipse, { x: 10.8, y: 4.6, w: 3.1, h: 3.1, fill: { color: "5E31C8", transparency: 18 }, line: { color: "5E31C8", transparency: 100 } });
  slide.addImage({ path: ICON, x: 0.78, y: 0.72, w: 0.52, h: 0.52 });
  slide.addText("ONLY MY FACE", { x: 1.45, y: 0.84, w: 2.8, h: 0.23, fontFace: "Arial", fontSize: 13, bold: true, color: "DCD2FF", charSpacing: 0.8, margin: 0 });
  slide.addText("사진 속 모든 얼굴을\n한 번에 가리는 방법", { x: 0.78, y: 1.75, w: 6.5, h: 1.35, fontFace: "Arial", fontSize: 32, bold: true, color: C.paper, breakLine: false, margin: 0, fit: "shrink" });
  slide.addText("블로그 업로드 전, 사진을 선택하고 결과를 저장하기까지", { x: 0.8, y: 3.38, w: 5.3, h: 0.3, fontFace: "Arial", fontSize: 14, color: "C8C2D9", margin: 0 });
  card(slide, 0.78, 4.35, 5.5, 1.2, "28203F");
  slide.addText("✓ 인터넷 업로드 없이 내 PC에서 처리\n✓ 모자이크 · 블러 · 예외 인물 설정 지원", { x: 1.08, y: 4.65, w: 4.8, h: 0.56, fontFace: "Arial", fontSize: 13, color: "F3F0FF", margin: 0, breakLine: false });
  slide.addImage({ path: SHOT, x: 7.3, y: 1.08, w: 5.3, h: 3.49, rounding: true, transparency: 0 });
  slide.addText("사용 안내 · v1.1.1 기준", { x: 0.8, y: 6.65, w: 4, h: 0.2, fontFace: "Arial", fontSize: 10, color: "AFA7C5", margin: 0 });
}

// 2. Start
{
  const slide = pptx.addSlide();
  slide.background = { color: C.paper };
  addTitle(slide, "STEP 01", "사진을 한 번에 추가하세요", "여러 장을 동시에 선택할 수 있고, 새로 선택하면 이전 결과는 자동으로 비워집니다.");
  card(slide, 0.62, 2.02, 8.0, 4.65, C.soft);
  slide.addImage({ path: SHOT, x: 0.9, y: 2.25, w: 7.45, h: 4.13 });
  slide.addShape(pptx.ShapeType.roundRect, { x: 1.08, y: 3.30, w: 1.72, h: 0.5, rectRadius: 0.08, fill: { color: C.violet, transparency: 84 }, line: { color: C.violet, width: 1.5 } });
  card(slide, 9.0, 2.1, 3.65, 1.3, C.violetLight);
  note(slide, 1, "파일 선택", "블로그에 올릴 사진을 여러 장 골라주세요.", 9.3, 2.47, 3.0);
  card(slide, 9.0, 3.72, 3.65, 1.56, C.paper);
  note(slide, 2, "새 사진 = 새 작업", "다른 사진을 선택하면 이전 처리 결과와 저장 대상이 사라집니다.", 9.3, 4.06, 3.0);
  card(slide, 9.0, 5.6, 3.65, 0.7, "EAF8F1");
  slide.addText("Tip  사진은 앱 밖으로 업로드되지 않습니다.", { x: 9.28, y: 5.84, w: 3.1, h: 0.2, fontFace: "Arial", fontSize: 10.5, bold: true, color: "18734B", margin: 0 });
  addFooter(slide, 1);
}

// 3. Settings
{
  const slide = pptx.addSlide();
  slide.background = { color: C.paper };
  addTitle(slide, "STEP 02", "가릴 방식과 범위를 정하세요", "처리 전 왼쪽 설정을 확인하고, 공개용 사진이면 ‘놓치지 않기’를 권장합니다.");
  card(slide, 0.62, 2.02, 8.0, 4.65, C.soft);
  slide.addImage({ path: SHOT, x: 0.9, y: 2.25, w: 7.45, h: 4.13 });
  slide.addShape(pptx.ShapeType.roundRect, { x: 1.03, y: 4.0, w: 2.12, h: 0.6, rectRadius: 0.08, fill: { color: C.violet, transparency: 88 }, line: { color: C.violet, width: 1.5 } });
  slide.addShape(pptx.ShapeType.roundRect, { x: 1.03, y: 5.4, w: 2.12, h: 1.95, rectRadius: 0.08, fill: { color: C.violet, transparency: 90 }, line: { color: C.violet, width: 1.5 } });
  note(slide, 1, "효과와 강도", "모자이크는 픽셀화, 블러는 흐리게 가립니다. 공개 사진은 강하게가 안전합니다.", 9.12, 2.22, 3.25);
  card(slide, 8.88, 3.44, 3.76, 1.44, C.paper);
  note(slide, 2, "얼굴 주변 여백", "숫자가 클수록 얼굴 바깥까지 넓게 가립니다. 옆얼굴에는 여백을 더 주세요.", 9.12, 3.76, 3.25);
  card(slide, 8.88, 5.23, 3.76, 1.18, C.violetLight);
  note(slide, 3, "얼굴 찾기: 놓치지 않기", "YuNet 얼굴 검출 뒤에 사람 상단 영역 안전망을 더해 옆·뒷모습도 넓게 가립니다.", 9.12, 5.49, 3.25);
  addFooter(slide, 2);
}

// 4. Process & save
{
  const slide = pptx.addSlide();
  slide.background = { color: C.soft };
  addTitle(slide, "STEP 03", "처리하고, 결과를 확인한 뒤 저장하세요", "얼굴을 놓치지 않았는지만 한 번 확인하면 블로그용 사진 준비가 끝납니다.");
  const steps = [
    ["사진 선택", "여러 장을 한 번에"],
    ["모든 얼굴 가리기", "로컬에서 자동 처리"],
    ["결과 확인", "옆·뒷모습도 확인"],
    ["결과 전체 저장", "원본은 그대로 유지"],
  ];
  steps.forEach((item, idx) => {
    const x = 0.77 + idx * 3.12;
    card(slide, x, 2.55, 2.57, 2.58, C.paper);
    slide.addShape(pptx.ShapeType.ellipse, { x: x + 0.92, y: 2.9, w: 0.72, h: 0.72, fill: { color: idx === 1 ? C.violet : C.violetLight }, line: { color: C.violet, transparency: 100 } });
    slide.addText(String(idx + 1), { x: x + 0.92, y: 3.08, w: 0.72, h: 0.2, fontFace: "Arial", fontSize: 14, bold: true, color: idx === 1 ? C.paper : C.violet, align: "center", margin: 0 });
    slide.addText(item[0], { x: x + 0.24, y: 3.92, w: 2.1, h: 0.24, fontFace: "Arial", fontSize: 14, bold: true, color: C.ink, align: "center", margin: 0, fit: "shrink" });
    slide.addText(item[1], { x: x + 0.25, y: 4.32, w: 2.08, h: 0.35, fontFace: "Arial", fontSize: 10.5, color: C.muted, align: "center", margin: 0, fit: "shrink" });
    if (idx < 3) slide.addShape(pptx.ShapeType.chevron, { x: x + 2.66, y: 3.47, w: 0.25, h: 0.34, fill: { color: "B9B1CD" }, line: { color: "B9B1CD" } });
  });
  card(slide, 1.45, 5.78, 10.45, 0.72, "EAF8F1");
  slide.addText("저장 전 확인: 사람의 얼굴·옆얼굴·뒷머리가 남아 있지 않은지 미리보기에서 확인하세요. ‘놓치지 않기’는 안전을 위해 넓은 영역을 가릴 수 있습니다.", { x: 1.76, y: 6.03, w: 9.85, h: 0.22, fontFace: "Arial", fontSize: 11, color: "18734B", margin: 0, fit: "shrink" });
  addFooter(slide, 3);
}

// 5. Summary
{
  const slide = pptx.addSlide();
  slide.background = { color: C.paper };
  addTitle(slide, "STEP 04", "자동으로 놓친 부분은 직접 가리세요", "처리 결과 카드에서 ‘놓친 부분 가리기’를 누르면, 사진 위를 드래그해 원하는 영역을 추가로 가릴 수 있습니다.");
  card(slide, 0.72, 2.15, 4.25, 4.28, C.soft);
  slide.addText("추가 가리기 예시", { x: 1.05, y: 2.45, w: 2.5, h: 0.24, fontFace: "Arial", fontSize: 14, bold: true, color: C.ink, margin: 0 });
  slide.addImage({ path: SAMPLE, x: 1.48, y: 2.95, w: 1.85, h: 1.85 });
  slide.addShape(pptx.ShapeType.roundRect, { x: 1.87, y: 3.55, w: 1.1, h: 0.57, rectRadius: 0.06, fill: { color: "1C2430", transparency: 10 }, line: { color: C.violet, width: 1.6, dash: "dash" } });
  slide.addText("드래그한\n가림 영역", { x: 3.46, y: 3.6, w: 0.75, h: 0.35, fontFace: "Arial", fontSize: 9, bold: true, color: C.violet, margin: 0, fit: "shrink" });
  slide.addShape(pptx.ShapeType.line, { x: 3.05, y: 3.83, w: 0.38, h: 0, line: { color: C.violet, width: 1.2, beginArrowType: "none", endArrowType: "triangle" } });
  slide.addText("현재 선택한 모자이크·블러\n설정이 그대로 적용됩니다.", { x: 1.05, y: 5.2, w: 3.4, h: 0.42, fontFace: "Arial", fontSize: 11, color: C.muted, align: "center", margin: 0 });
  const manualSteps = [
    ["1", "결과 카드에서", "‘놓친 부분 가리기’를 누르세요."],
    ["2", "사진 위를 드래그", "남은 얼굴이나 민감한 부분을 넓게 선택하세요."],
    ["3", "계속 가리거나 완료", "여러 영역을 반복해서 가린 뒤 완료를 누르세요."],
  ];
  manualSteps.forEach((item, idx) => {
    const y = 2.25 + idx * 1.28;
    card(slide, 5.48, y, 6.95, 0.93, idx === 1 ? C.violetLight : C.soft);
    bubble(slide, item[0], 5.82, y + 0.27);
    slide.addText(item[1], { x: 6.43, y: y + 0.2, w: 2.0, h: 0.2, fontFace: "Arial", fontSize: 13, bold: true, color: C.ink, margin: 0 });
    slide.addText(item[2], { x: 8.46, y: y + 0.22, w: 3.56, h: 0.24, fontFace: "Arial", fontSize: 10.5, color: C.muted, margin: 0, fit: "shrink" });
  });
  card(slide, 5.48, 6.15, 6.95, 0.36, "FFF4E5");
  slide.addText("Tip  이 단계는 원본을 건드리지 않고, 처리 결과에만 추가로 반영됩니다.", { x: 5.78, y: 6.26, w: 6.3, h: 0.14, fontFace: "Arial", fontSize: 9.5, bold: true, color: "9A4C00", margin: 0, fit: "shrink" });
  addFooter(slide, 4);
}

// 5. Summary
{
  const slide = pptx.addSlide();
  slide.background = { color: C.paper };
  slide.addImage({ path: SAMPLE, x: 0.86, y: 1.25, w: 2.15, h: 2.15 });
  slide.addShape(pptx.ShapeType.roundRect, { x: 1.2, y: 2.2, w: 1.47, h: 0.55, rectRadius: 0.08, fill: { color: "1C2430" }, line: { color: "1C2430" } });
  slide.addText("공개 전 확인", { x: 3.62, y: 1.33, w: 5.1, h: 0.5, fontFace: "Arial", fontSize: 28, bold: true, color: C.ink, margin: 0 });
  slide.addText("완벽한 자동 검출은 없으므로, 저장하기 전 결과를 한 번만 살펴보세요.", { x: 3.64, y: 1.98, w: 6.8, h: 0.28, fontFace: "Arial", fontSize: 13, color: C.muted, margin: 0 });
  const checks = [
    ["얼굴이 모두 가려졌나요?", "정면·옆얼굴·숙인 얼굴까지 확인"],
    ["가림 범위가 충분한가요?", "필요하면 여백 또는 강도를 높이기"],
    ["예외 인물이 있나요?", "예외 인물 관리에서 등록·수정·삭제"],
  ];
  checks.forEach((item, idx) => {
    const y = 2.82 + idx * 1.05;
    card(slide, 3.6, y, 7.9, 0.78, idx === 2 ? C.violetLight : C.soft);
    slide.addShape(pptx.ShapeType.ellipse, { x: 3.9, y: y + 0.18, w: 0.34, h: 0.34, fill: { color: idx === 2 ? C.violet : C.mint }, line: { color: idx === 2 ? C.violet : C.mint } });
    slide.addText("✓", { x: 3.9, y: y + 0.195, w: 0.34, h: 0.15, fontFace: "Arial", fontSize: 10, bold: true, color: C.paper, align: "center", margin: 0 });
    slide.addText(item[0], { x: 4.5, y: y + 0.15, w: 2.8, h: 0.2, fontFace: "Arial", fontSize: 12.5, bold: true, color: C.ink, margin: 0 });
    slide.addText(item[1], { x: 7.55, y: y + 0.16, w: 3.5, h: 0.2, fontFace: "Arial", fontSize: 10.5, color: C.muted, margin: 0, fit: "shrink" });
  });
  slide.addText("Only My Face", { x: 0.88, y: 4.28, w: 2.1, h: 0.23, fontFace: "Arial", fontSize: 15, bold: true, color: C.violet, align: "center", margin: 0 });
  slide.addText("안전하게 가리고\n편하게 기록하세요.", { x: 0.8, y: 4.75, w: 2.28, h: 0.65, fontFace: "Arial", fontSize: 14, bold: true, color: C.ink, align: "center", margin: 0 });
  addFooter(slide, 5);
}

pptx.writeFile({ fileName: path.join(__dirname, "OnlyMyFace_사용안내.pptx") });
