# Next.js PWA with Tailwind CSS and Framer Motion

This project is a Next.js application that is configured as a Progressive Web App (PWA) with Tailwind CSS for styling and Framer Motion for animations. 

## Project Structure

```
next-pwa-app
├── public
│   └── manifest.json          # PWA manifest configuration
├── src
│   └── app
│       ├── globals.css        # Tailwind CSS styles
│       └── page.tsx          # Main landing page component
├── next.config.js             # Next.js configuration
├── package.json                # npm configuration and dependencies
├── postcss.config.js          # PostCSS configuration
├── tailwind.config.js         # Tailwind CSS configuration
└── README.md                  # Project documentation
```

## Setup Instructions

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd next-pwa-app
   ```

2. **Install dependencies:**
   ```bash
   npm install
   ```

3. **Run the development server:**
   ```bash
   npm run dev
   ```

4. **Open your browser and navigate to:**
   ```
   http://localhost:3000
   ```

## Usage

- The application features a landing page with a spiral background animation created using Framer Motion.
- The PWA manifest is located in `public/manifest.json`, which defines the app's name, icons, and display settings.
- Tailwind CSS is used for styling, and the styles are imported in `src/app/globals.css`.

## Building for Production

To build the application for production, run:

```bash
npm run build
```

Then, you can start the production server with:

```bash
npm start
```

## Additional Notes

- Icons for the PWA can be generated using tools like [pwa-assets-generator](https://www.npmjs.com/package/pwa-asset-generator).
- Customize the Tailwind CSS configuration in `tailwind.config.js` to fit your design needs.