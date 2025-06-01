import React from 'react';

const Ripple = ({ 
  color = "#000000", 
  size = "medium", 
  text = "", 
  textColor = "" 
}) => {
  // Size configurations
  const sizeConfig = {
    small: {
      containerSize: '24px',
      rippleSize: '6px',
      fontSize: '0.75rem'
    },
    medium: {
      containerSize: '40px',
      rippleSize: '10px',
      fontSize: '0.875rem'
    },
    large: {
      containerSize: '60px',
      rippleSize: '15px',
      fontSize: '1rem'
    }
  };

  const config = sizeConfig[size] || sizeConfig.medium;
  const finalTextColor = textColor || color;

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      gap: text ? '12px' : '0'
    }}>
      {/* Ripple Animation Container */}
      <div style={{
        position: 'relative',
        width: config.containerSize,
        height: config.containerSize,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center'
      }}>
        {/* Ripple Circles */}
        {[0, 1, 2].map((index) => (
          <div
            key={index}
            style={{
              position: 'absolute',
              width: config.rippleSize,
              height: config.rippleSize,
              borderRadius: '50%',
              backgroundColor: color,
              animation: `ripple 1.5s infinite ${index * 0.2}s`,
              opacity: 0
            }}
          />
        ))}
      </div>

      {/* Optional Text */}
      {text && (
        <div style={{
          color: finalTextColor,
          fontSize: config.fontSize,
          fontWeight: '500',
          textAlign: 'center',
          fontFamily: 'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
        }}>
          {text}
        </div>
      )}

      {/* CSS Animation */}
      <style jsx>{`
        @keyframes ripple {
          0% {
            transform: scale(0);
            opacity: 1;
          }
          100% {
            transform: scale(2.5);
            opacity: 0;
          }
        }
      `}</style>
    </div>
  );
};

export default Ripple;
