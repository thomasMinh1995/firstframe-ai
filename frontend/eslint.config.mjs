import {fileURLToPath} from 'node:url';
import {FlatCompat} from '@eslint/eslintrc';

const compat = new FlatCompat({baseDirectory: fileURLToPath(new URL('.', import.meta.url))});
export default [
  {ignores: ['.next/**', 'node_modules/**']},
  ...compat.extends('next/core-web-vitals'),
];
