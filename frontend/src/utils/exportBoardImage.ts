/**
 * exportBoardImage — renders the detective board canvas to a PNG image
 * using the native Canvas API (no external libraries).
 *
 * Approach:
 *  1. Clone the board inner element
 *  2. Convert the clone to a data URL via SVG foreignObject
 *  3. Draw to an offscreen canvas at 2x for retina quality
 *  4. Trigger a download as PNG
 *
 * This avoids any dependency on html-to-image or html2canvas.
 */

/**
 * Export the board canvas element as a downloadable PNG.
 *
 * @param boardElement The `.board-canvas__inner` DOM element
 * @param filename     Output file name (default: detective-board.png)
 */
export async function exportBoardImage(
  boardElement: HTMLElement,
  filename = 'detective-board.png',
): Promise<void> {
  // Measure the board's bounding dimensions
  const rect = boardElement.getBoundingClientRect();
  const width = Math.max(rect.width, 800);
  const height = Math.max(rect.height, 600);
  const scale = 2; // retina

  // Collect all stylesheets into a single <style> string
  const styleSheets = Array.from(document.styleSheets);
  let cssText = '';
  for (const sheet of styleSheets) {
    try {
      const rules = Array.from(sheet.cssRules);
      for (const rule of rules) {
        cssText += rule.cssText + '\n';
      }
    } catch {
      // Cross-origin stylesheets will throw — skip them
    }
  }

  // Clone the board element
  const clone = boardElement.cloneNode(true) as HTMLElement;
  clone.style.transform = 'none'; // reset zoom/pan for export
  clone.style.position = 'relative';
  clone.style.width = `${width}px`;
  clone.style.height = `${height}px`;

  // Wrap in an SVG foreignObject for rendering
  const svgData = `
    <svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}">
      <foreignObject width="100%" height="100%">
        <div xmlns="http://www.w3.org/1999/xhtml">
          <style>${cssText}</style>
          ${clone.outerHTML}
        </div>
      </foreignObject>
    </svg>
  `;

  const svgBlob = new Blob([svgData], {
    type: 'image/svg+xml;charset=utf-8',
  });
  const url = URL.createObjectURL(svgBlob);

  return new Promise<void>((resolve, reject) => {
    const img = new Image();
    img.onload = () => {
      const canvas = document.createElement('canvas');
      canvas.width = width * scale;
      canvas.height = height * scale;
      const ctx = canvas.getContext('2d');

      if (!ctx) {
        URL.revokeObjectURL(url);
        reject(new Error('Could not get 2D context'));
        return;
      }

      ctx.scale(scale, scale);
      // Background
      ctx.fillStyle = '#1a1a2e';
      ctx.fillRect(0, 0, width, height);
      ctx.drawImage(img, 0, 0, width, height);

      URL.revokeObjectURL(url);

      // Trigger download
      canvas.toBlob((blob) => {
        if (!blob) {
          reject(new Error('Canvas toBlob returned null'));
          return;
        }
        const downloadUrl = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = downloadUrl;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(downloadUrl);
        resolve();
      }, 'image/png');
    };

    img.onerror = () => {
      URL.revokeObjectURL(url);
      reject(new Error('Failed to load SVG for export'));
    };

    img.src = url;
  });
}
