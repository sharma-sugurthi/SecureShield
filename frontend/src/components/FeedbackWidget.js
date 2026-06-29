'use client';

import { useState, useEffect } from 'react';
import { X, Star, MessageSquareHeart } from 'lucide-react';
import { submitFeedback } from '../lib/api';

export default function FeedbackWidget() {
  const [isOpen, setIsOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState('');
  const [showRateLabel, setShowRateLabel] = useState(false);

  // Show "Rate Us" tooltip every 5 minutes for 8 seconds
  useEffect(() => {
    // Show once after 10 seconds on first load
    const initialTimer = setTimeout(() => {
      setShowRateLabel(true);
      setTimeout(() => setShowRateLabel(false), 8000);
    }, 10000);

    // Then repeat every 5 minutes
    const interval = setInterval(() => {
      setShowRateLabel(true);
      setTimeout(() => setShowRateLabel(false), 8000);
    }, 5 * 60 * 1000);

    return () => {
      clearTimeout(initialTimer);
      clearInterval(interval);
    };
  }, []);

  const [formData, setFormData] = useState({
    accuracy_rating: 0,
    claim_rejections: '',
    problem_solving: '',
    addon_suggestions: '',
    knowledge_source: '',
    govt_regulations: '',
    developer_centric: '',
    other_suggestions: ''
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
          developer_centric: '',
          other_suggestions: ''
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
        className="feedback-trigger"
        onClick={() => { setIsOpen(true); setShowRateLabel(false); }}
        style={{
          position: 'fixed',
          bottom: '24px',
          right: '24px',
          zIndex: 40,
          backgroundColor: 'var(--primary-600)',
          color: 'var(--white)',
          padding: '12px',
          borderRadius: '50%',
          boxShadow: '0 10px 15px -3px rgba(79, 70, 229, 0.3)',
          border: 'none',
          cursor: 'pointer',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          transition: 'all 0.3s ease',
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.transform = 'scale(1.05)';
          e.currentTarget.style.backgroundColor = 'var(--primary-700)';
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.transform = 'scale(1)';
          e.currentTarget.style.backgroundColor = 'var(--primary-600)';
        }}
        title="Rate This App"
      >
        <MessageSquareHeart size={24} />
      </button>

      {/* Rate Us tooltip — appears periodically */}
      <div
        className="rate-us-tooltip"
        onClick={() => { setIsOpen(true); setShowRateLabel(false); }}
        style={{
          position: 'fixed',
          bottom: '30px',
          right: '72px',
          zIndex: 39,
          backgroundColor: 'var(--navy-800)',
          color: 'white',
          padding: '8px 16px',
          borderRadius: '20px',
          fontSize: '13px',
          fontWeight: 600,
          cursor: 'pointer',
          boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
          whiteSpace: 'nowrap',
          opacity: showRateLabel ? 1 : 0,
          transform: showRateLabel ? 'translateX(0)' : 'translateX(20px)',
          transition: 'opacity 0.4s ease, transform 0.4s ease',
          pointerEvents: showRateLabel ? 'auto' : 'none',
        }}
      >
        ⭐ Rate Us!
      </div>

      {isOpen && (
        <div className="feedback-overlay" style={{
          position: 'fixed',
          top: 0, left: 0, right: 0, bottom: 0,
          zIndex: 9999,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          padding: '16px'
        }}>
          {/* Backdrop */}
          <div 
            style={{
              position: 'fixed',
              top: 0, left: 0, right: 0, bottom: 0,
              backgroundColor: 'rgba(15, 23, 42, 0.6)',
              backdropFilter: 'blur(4px)',
            }}
            onClick={() => setIsOpen(false)} 
          />

          {/* Modal */}
          <div className="feedback-modal" style={{
            position: 'relative',
            width: '100%',
            maxWidth: '600px',
            backgroundColor: 'var(--white)',
            borderRadius: 'var(--radius-xl)',
            boxShadow: 'var(--shadow-xl)',
            padding: '24px',
            maxHeight: 'calc(100vh - 140px)',
            display: 'flex',
            flexDirection: 'column'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '20px' }}>
              <h3 style={{ fontSize: '20px', fontWeight: 800, color: 'var(--navy-900)' }}>Help Us Make PolicyEye Smarter</h3>
              <button 
                onClick={() => setIsOpen(false)} 
                style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--gray-400)' }}
              >
                <X size={20} />
              </button>
            </div>

            {submitted ? (
              <div style={{ padding: '48px 0', textAlign: 'center' }}>
                <div style={{
                  width: '64px', height: '64px', backgroundColor: 'var(--green-50)', color: 'var(--green-600)',
                  borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center',
                  margin: '0 auto 16px'
                }}>
                  <Star size={32} fill="currentColor" />
                </div>
                <h4 style={{ fontSize: '18px', fontWeight: 600, color: 'var(--navy-900)', marginBottom: '8px' }}>Thank you for your insights!</h4>
                <p style={{ color: 'var(--gray-500)', fontSize: '14px' }}>Your feedback helps us train a better AI and improve the application. We've sent a thank you note to your email.</p>
              </div>
            ) : (
              <form onSubmit={handleSubmit} style={{ overflowY: 'auto', paddingRight: '8px', display: 'flex', flexDirection: 'column', gap: '20px' }}>
                {error && (
                  <div style={{ padding: '12px', fontSize: '14px', color: 'var(--red-600)', backgroundColor: 'var(--red-50)', borderRadius: 'var(--radius-md)' }}>
                    {error}
                  </div>
                )}

                <div>
                  <label className="form-label" style={{ display: 'block', marginBottom: '8px' }}>
                    1. How accurate was the AI in analyzing your policy? <span style={{ color: 'var(--red-500)' }}>*</span>
                  </label>
                  <div style={{ display: 'flex', gap: '8px' }}>
                    {[1, 2, 3, 4, 5].map((star) => (
                      <button
                        key={star}
                        type="button"
                        onClick={() => setFormData({ ...formData, accuracy_rating: star })}
                        style={{
                          background: 'none', border: 'none', cursor: 'pointer',
                          color: formData.accuracy_rating >= star ? 'var(--amber-500)' : 'var(--gray-200)',
                          transition: 'color 0.2s'
                        }}
                      >
                        <Star size={32} fill="currentColor" />
                      </button>
                    ))}
                  </div>
                </div>

                <div>
                  <label className="form-label" style={{ display: 'block', marginBottom: '8px' }}>
                    2. Have you faced any previous policy claim rejections? What were they?
                  </label>
                  <textarea
                    name="claim_rejections"
                    value={formData.claim_rejections}
                    onChange={handleChange}
                    rows={3}
                    className="form-input"
                    style={{ resize: 'vertical' }}
                  />
                </div>

                <div>
                  <label className="form-label" style={{ display: 'block', marginBottom: '8px' }}>
                    3. Do you think this application can solve your insurance policy claim problems?
                  </label>
                  <textarea
                    name="problem_solving"
                    value={formData.problem_solving}
                    onChange={handleChange}
                    rows={2}
                    className="form-input"
                    style={{ resize: 'vertical' }}
                  />
                </div>

                <div>
                  <label className="form-label" style={{ display: 'block', marginBottom: '8px' }}>
                    4. Any addon suggestions like Joint/Group insurance, Accidental, Life insurance, etc.?
                  </label>
                  <textarea
                    name="addon_suggestions"
                    value={formData.addon_suggestions}
                    onChange={handleChange}
                    rows={2}
                    className="form-input"
                    style={{ resize: 'vertical' }}
                  />
                </div>

                <div>
                  <label className="form-label" style={{ display: 'block', marginBottom: '8px' }}>
                    5. If you are in insurance: presently the application is not well versed with specific city details/local policies. Where can we get this information from?
                  </label>
                  <textarea
                    name="knowledge_source"
                    value={formData.knowledge_source}
                    onChange={handleChange}
                    rows={2}
                    className="form-input"
                    style={{ resize: 'vertical' }}
                  />
                </div>

                <div>
                  <label className="form-label" style={{ display: 'block', marginBottom: '8px' }}>
                    6. If you're in govt: do you think this application follows govt regulations? If not, how and why?
                  </label>
                  <textarea
                    name="govt_regulations"
                    value={formData.govt_regulations}
                    onChange={handleChange}
                    rows={2}
                    className="form-input"
                    style={{ resize: 'vertical' }}
                  />
                </div>

                <div>
                  <label className="form-label" style={{ display: 'block', marginBottom: '8px' }}>
                    7. Did you encounter any technical bugs, UI issues, or have feature suggestions?
                  </label>
                  <textarea
                    name="developer_centric"
                    value={formData.developer_centric}
                    onChange={handleChange}
                    rows={2}
                    className="form-input"
                    style={{ resize: 'vertical' }}
                  />
                </div>

                <div>
                  <label className="form-label" style={{ display: 'block', marginBottom: '8px' }}>
                    8. Any other suggestions or questions for us?
                  </label>
                  <textarea
                    name="other_suggestions"
                    value={formData.other_suggestions}
                    onChange={handleChange}
                    rows={3}
                    className="form-input"
                    style={{ resize: 'vertical' }}
                    placeholder="Share anything else on your mind..."
                  />
                </div>

                <div style={{ paddingTop: '16px', borderTop: '1px solid var(--gray-100)', display: 'flex', justifyContent: 'flex-end', gap: '12px' }}>
                  <button
                    type="button"
                    onClick={() => setIsOpen(false)}
                    className="btn btn-secondary"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={isSubmitting}
                    className="btn btn-primary"
                  >
                    {isSubmitting ? 'Submitting...' : 'Submit Feedback'}
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>
      )}
    </>
  );
}
