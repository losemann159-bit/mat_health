import { cp, mkdir, readFile, writeFile } from 'node:fs/promises';

await mkdir('dist', { recursive: true });
await cp('data/photos', 'dist/photos', { recursive: true });
await cp('data/journal.json', 'dist/journal.json');
const html = await readFile('index.html', 'utf8');
await writeFile('dist/index.html', html);
