import { Analytics } from '@vercel/analytics/next'
import type { Metadata, Viewport } from 'next'
import './globals.css'

// 1. MANUALLY UPDATE THE METADATA OBJECT HERE
export const metadata: Metadata = {
  title: 'Trendlens — Predictive Asset Horizon & Forecasting',
  description: 'Trendlens turns volatile crude oil tariffs, real estate asset variables, and air quality indexes into predictable values.',
  generator: 'v0.app',
  icons: {
    icon: [
      {
        url: '/icon-light-32x32.png',
        media: '(prefers-color-scheme: light)',
      },
      {
        url: '/icon-dark-32x32.png',
        media: '(prefers-color-scheme: dark)',
      },
      {
        url: '/icon.svg',
        type: 'image/svg+xml',
      },
    ],
    apple: '/apple-icon.png',
  },
}

export const viewport: Viewport = {
  colorScheme: 'light dark',
  themeColor: [
    { media: '(prefers-color-scheme: light)', color: '#FDFBF7' }, // Updated to match your warm cream base
    { media: '(prefers-color-scheme: dark)', color: '#4A1521' },  // Updated to match your deep maroon theme
  ],
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="en">
      <body className="antialiased bg-[#FDFBF7]"> {/* Added your cream base color to the body fallback */}
        {children}
        {process.env.NODE_ENV === 'production' && <Analytics />}
      </body>
    </html>
  )
}
