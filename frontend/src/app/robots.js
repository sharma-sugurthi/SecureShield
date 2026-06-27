export default function robots() {
  return {
    rules: [
      {
        userAgent: '*',
        allow: '/',
        disallow: ['/api/', '/settings'],
      },
    ],
    sitemap: 'https://www.policyeye.app/sitemap.xml',
    host: 'https://www.policyeye.app',
  };
}
