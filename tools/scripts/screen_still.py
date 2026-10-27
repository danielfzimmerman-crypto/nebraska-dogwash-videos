# screen_still.py IN.png OUT.png kind "x0,y0,x1,y1,x2,y2,x3,y3" [mode]
# Put the lookalike menu art (kind = main|side) onto one screen of a still, corners TL,TR,BR,BL.
# mode "key": only replace blue pixels (keeps hair/dogs in front). mode "hair": replace everything except
# warm-coloured hair/skin. mode "all": replace the whole quad.
import sys, os, numpy as np, cv2
IN, OUT, kind, pts = sys.argv[1:5]; mode = sys.argv[5] if len(sys.argv) > 5 else 'all'
ART = os.path.dirname(os.path.abspath(__file__)) + '/../specs/'
art = cv2.imread(ART + ('screen_main.png' if kind == 'main' else 'screen_side.png'))
f = cv2.imread(IN).astype(np.float32); H, W = f.shape[:2]
q = np.float32([float(v) for v in pts.split(',')]).reshape(4, 2)
src = np.float32([[0, 0], [art.shape[1], 0], [art.shape[1], art.shape[0]], [0, art.shape[0]]])
warped = cv2.warpPerspective(art, cv2.getPerspectiveTransform(src, q), (W, H), flags=cv2.INTER_AREA).astype(np.float32)
warped = cv2.GaussianBlur(warped, (3, 3), 0) * .93
poly = np.zeros((H, W), np.float32); cv2.fillConvexPoly(poly, q.astype(np.int32), 1.)
hsv = cv2.cvtColor(f.astype(np.uint8), cv2.COLOR_BGR2HSV).astype(np.float32)
if mode == 'key':
    m = (np.clip((hsv[..., 1] - 90) / 60, 0, 1) * np.clip((hsv[..., 2] - 80) / 60, 0, 1) * np.clip(1 - np.abs(hsv[..., 0] - 113) / 18, 0, 1) * 1.6).clip(0, 1)
elif mode == 'hair':
    warm = ((hsv[..., 0] > 5) & (hsv[..., 0] < 35) & (hsv[..., 1] > 50)).astype(np.float32)
    warm = cv2.dilate(warm, np.ones((5, 5), np.uint8)); m = 1 - cv2.GaussianBlur(warm, (0, 0), 1.5)
else:
    m = np.ones((H, W), np.float32)
a = (cv2.GaussianBlur(poly, (0, 0), 1) * m)[..., None]
cv2.imwrite(OUT, (f * (1 - a) + warped * a).clip(0, 255).astype(np.uint8))
print('ok', OUT)
