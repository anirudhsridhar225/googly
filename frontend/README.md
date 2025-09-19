This is a [Next.js](https://nextjs.org) project bootstrapped with [`create-next-app`](https://nextjs.org/docs/app/api-reference/cli/create-next-app).

## Progressive Web App (PWA)

This application is a fully functional Progressive Web App with installability, offline support, and mobile-friendly features.

### PWA Features

- **Installable**: Can be installed on desktop and mobile devices
- **Offline Support**: Works offline with cached content
- **Responsive**: Works on all device sizes
- **Fast**: Loads quickly and functions smoothly
- **Secure**: Served over HTTPS when deployed

### Installation

The application can be installed on any device that supports PWAs:

**Desktop**
- **Chrome**: Click the install icon in the address bar
- **Edge**: Click the install icon in the address bar
- **Firefox**: Click the install icon in the address bar

**Mobile**
- **Android (Chrome)**: Click the menu (three dots) → Add to Home Screen
- **iOS (Safari)**: Click the share icon → Add to Home Screen

## Getting Started

First, run the development server:

```bash
npm run dev
# or
yarn dev
# or
pnpm dev
# or
bun dev
```

Open [http://localhost:3000](http://localhost:3000) with your browser to see the result.

You can start editing the page by modifying `app/page.tsx`. The page auto-updates as you edit the file.

This project uses [`next/font`](https://nextjs.org/docs/app/building-your-application/optimizing/fonts) to automatically optimize and load [Geist](https://vercel.com/font), a new font family for Vercel.

## Learn More

To learn more about Next.js, take a look at the following resources:

- [Next.js Documentation](https://nextjs.org/docs) - learn about Next.js features and API.
- [Learn Next.js](https://nextjs.org/learn) - an interactive Next.js tutorial.

You can check out [the Next.js GitHub repository](https://github.com/vercel/next.js) - your feedback and contributions are welcome!

## Deploy on Vercel

The easiest way to deploy your Next.js app is to use the [Vercel Platform](https://vercel.com/new?utm_medium=default-template&filter=next.js&utm_source=create-next-app&utm_campaign=create-next-app-readme) from the creators of Next.js.

Check out our [Next.js deployment documentation](https://nextjs.org/docs/app/building-your-application/deploying) for more details.

### PWA Deployment Notes

When deploying this PWA, ensure your hosting platform supports:
1. HTTPS (required for PWA installation)
2. Proper serving of static assets (manifest.json, icons, etc.)
3. Correct MIME types for all files

See `README_PWA.md` for more detailed deployment instructions.
