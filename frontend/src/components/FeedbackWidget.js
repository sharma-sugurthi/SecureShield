'use client';

import { useState } from 'react';
import { X, Star, MessageSquareHeart } from 'lucide-react';
import { submitFeedback } from '../lib/api';

export default function FeedbackWidget() {
  const [isOpen, setIsOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState('');

  const [formData, setFormData] = useState({
    accuracy_rating: 0,
    claim_rejections: '',
    problem_solving: '',
    addon_suggestions: '',
    knowledge_source: '',
    govt_regulations: '',
    developer_centric: ''
  });

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (formData.accuracy_rating === 0) {
      setError('Please provide an accuracy rating first.');
      return;
    }
    setError('');
    setIsSubmitting(true);
    
    try {
      await submitFeedback(formData);
      setSubmitted(true);
      setTimeout(() => {
        setIsOpen(false);
        setSubmitted(false);
        setFormData({
          accuracy_rating: 0,
          claim_rejections: '',
          problem_solving: '',
          addon_suggestions: '',
          knowledge_source: '',
          govt_regulations: '',
          developer_centric: ''
        });
      }, 3000);
    } catch (err) {
      setError(err.message || 'Failed to submit feedback. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <>
      <button
        onClick={() => setIsOpen(true)}
        className="fixed bottom-6 right-6 z-40 bg-indigo-600 hover:bg-indigo-700 text-white p-3 rounded-full shadow-lg shadow-indigo-600/30 transition-all hover:scale-105 flex items-center justify-center group"
        title="Give Feedback"
      >
        <MessageSquareHeart size={24} />
        <span className="max-w-0 overflow-hidden whitespace-nowrap group-hover:max-w-xs transition-all duration-300 ease-in-out font-medium ml-0 group-hover:ml-2">
          Rate App
        </span>
      </button>

      {isOpen && (
        <div className="fixed inset-0 z-50 overflow-y-auto">
          <div className="flex items-center justify-center min-h-screen px-4 pt-4 pb-20 text-center sm:p-0">
            <div className="fixed inset-0 transition-opacity bg-slate-900/60 backdrop-blur-sm" onClick={() => setIsOpen(false)} />

            <div className="relative inline-block w-full max-w-2xl p-6 overflow-hidden text-left align-middle transition-all transform bg-white shadow-xl rounded-2xl">
              <div className="flex items-center justify-between mb-5">
                <h3 className="text-xl font-bold text-slate-900">Help Us Make PolicyEye Smarter</h3>
                <button onClick={() => setIsOpen(false)} className="text-slate-400 hover:text-slate-600 transition-colors">
                  <X size={20} />
                </button>
              </div>

              {submitted ? (
                <div className="py-12 text-center">
                  <div className="w-16 h-16 bg-green-100 text-green-600 rounded-full flex items-center justify-center mx-auto mb-4">
                    <Star size={32} fill="currentColor" />
                  </div>
                  <h4 className="text-lg font-semibold text-slate-900 mb-2">Thank you for your insights!</h4>
                  <p className="text-slate-600">Your feedback helps us train a better AI and improve the application. We've sent a thank you note to your email.</p>
                </div>
              ) : (
                <form onSubmit={handleSubmit} className="space-y-6 max-h-[70vh] overflow-y-auto pr-2 custom-scrollbar">
                  {error && (
                    <div className="p-3 text-sm text-red-600 bg-red-50 rounded-lg">{error}</div>
                  )}

                  <div className="space-y-3">
                    <label className="block text-sm font-medium text-slate-700">
                      1. How accurate was the AI in analyzing your policy? <span className="text-red-500">*</span>
                    </label>
                    <div className="flex gap-2">
                      {[1, 2, 3, 4, 5].map((star) => (
                        <button
                          key={star}
                          type="button"
                          onClick={() => setFormData({ ...formData, accuracy_rating: star })}
                          className={`p-1 transition-colors ${formData.accuracy_rating >= star ? 'text-amber-400' : 'text-slate-200 hover:text-amber-200'}`}
                        >
                          <Star size={32} fill="currentColor" />
                        </button>
                      ))}
                    </div>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-2">
                      2. Have you faced any previous policy claim rejections? What were they? Share your experience.
                    </label>
                    <textarea
                      name="claim_rejections"
                      value={formData.claim_rejections}
                      onChange={handleChange}
                      rows={3}
                      className="w-full px-3 py-2 text-sm border rounded-lg border-slate-300 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none"
                      placeholder="e.g., Yes, my room rent was capped and they rejected the rest..."
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-2">
                      3. Do you think this application can solve your insurance policy claim problems?
                    </label>
                    <textarea
                      name="problem_solving"
                      value={formData.problem_solving}
                      onChange={handleChange}
                      rows={2}
                      className="w-full px-3 py-2 text-sm border rounded-lg border-slate-300 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none"
                      placeholder="Yes/No, because..."
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-2">
                      4. Any addon suggestions like Joint/Group insurance, Accidental, Life insurance, etc.?
                    </label>
                    <textarea
                      name="addon_suggestions"
                      value={formData.addon_suggestions}
                      onChange={handleChange}
                      rows={2}
                      className="w-full px-3 py-2 text-sm border rounded-lg border-slate-300 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-2">
                      5. If you are in insurance: presently the application is not well versed with specific city details/local policies. Where can we get this information from?
                    </label>
                    <textarea
                      name="knowledge_source"
                      value={formData.knowledge_source}
                      onChange={handleChange}
                      rows={2}
                      className="w-full px-3 py-2 text-sm border rounded-lg border-slate-300 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none"
                      placeholder="e.g., IRDAI state portals, specific TPA websites..."
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-2">
                      6. If you're in govt: do you think this application follows govt regulations? If not, how and why?
                    </label>
                    <textarea
                      name="govt_regulations"
                      value={formData.govt_regulations}
                      onChange={handleChange}
                      rows={2}
                      className="w-full px-3 py-2 text-sm border rounded-lg border-slate-300 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-2">
                      7. Did you encounter any technical bugs, UI issues, or have feature suggestions for the developers?
                    </label>
                    <textarea
                      name="developer_centric"
                      value={formData.developer_centric}
                      onChange={handleChange}
                      rows={2}
                      className="w-full px-3 py-2 text-sm border rounded-lg border-slate-300 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none"
                      placeholder="e.g., The upload button is too small on mobile..."
                    />
                  </div>

                  <div className="pt-4 flex justify-end gap-3 border-t">
                    <button
                      type="button"
                      onClick={() => setIsOpen(false)}
                      className="px-4 py-2 text-sm font-medium text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-lg transition-colors"
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      disabled={isSubmitting}
                      className="px-4 py-2 text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 rounded-lg transition-colors disabled:opacity-50 flex items-center gap-2"
                    >
                      {isSubmitting ? 'Submitting...' : 'Submit Feedback'}
                    </button>
                  </div>
                </form>
              )}
            </div>
          </div>
        </div>
      )}
    </>
  );
}
