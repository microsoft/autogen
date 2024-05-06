/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  images: {
    domains: ['dalleproduse.blob.core.windows.net'],
    remotePatterns: [
      {
        protocol: 'https',
        hostname: 'dalleproduse.blob.core.windows.net',
        port: '**',
        pathname: '**',
      },
    ],
  },
};

export default nextConfig;