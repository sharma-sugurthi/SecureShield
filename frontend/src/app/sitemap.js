export default function sitemap() {
  const baseUrl = 'https://www.policyeye.app';

  const routes = [
    { path: '/', priority: 1.0, changeFreq: 'daily' },
    { path: '/about', priority: 0.9, changeFreq: 'weekly' },
    { path: '/how-it-works', priority: 0.9, changeFreq: 'weekly' },
    { path: '/chat', priority: 0.8, changeFreq: 'daily' },
    { path: '/login', priority: 0.7, changeFreq: 'monthly' },
    { path: '/signup', priority: 0.7, changeFreq: 'monthly' },
    { path: '/upload', priority: 0.8, changeFreq: 'daily' },
    { path: '/check', priority: 0.8, changeFreq: 'daily' },
    { path: '/dispute', priority: 0.7, changeFreq: 'weekly' },
    { path: '/history', priority: 0.6, changeFreq: 'daily' },
    { path: '/audit', priority: 0.5, changeFreq: 'daily' },
  ];

  return routes.map((route) => ({
    url: `${baseUrl}${route.path}`,
    lastModified: new Date(),
    changeFrequency: route.changeFreq,
    priority: route.priority,
  }));
}
