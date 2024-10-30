/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  images: {
    domains: ['dalleprodsec.blob.core.windows.net', 'oaidalleapiprodscus.blob.core.windows.net'],
    remotePatterns: [
      {
        protocol: 'https',
        hostname: 'dalleprodsec.blob.core.windows.net',
        port: '**',
        pathname: '**',
      },
      {
        protocol: 'https',
        hostname: 'oaidalleapiprodscus.blob.core.windows.net',
        port: '**',
        pathname: '**',
      },
    ],
  },
};

export default nextConfig;
