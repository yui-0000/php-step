const response = await fetch('/api/questions');
if (!response.ok) throw new Error('問題を読み込めませんでした');
const content = await response.json();
export const questions = content.questions;
export const topics = content.topics;
