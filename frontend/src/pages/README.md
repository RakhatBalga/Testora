This directory is reserved for the Feature-Sliced Design `pages` layer.

Testora currently uses the Next.js App Router in `src/app`, and Next.js treats
TypeScript files inside `src/pages` as Pages Router routes. Keep this layer free
of route modules until the project adopts a route-file convention that prevents
that conflict.
