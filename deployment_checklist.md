# Production Deployment Checklist

## Before Deployment
- [ ] Change all default passwords
- [ ] Set `DEBUG=False` in production
- [ ] Generate new `SECRET_KEY`
- [ ] Set `ALLOWED_HOSTS` to your domain
- [ ] Configure PostgreSQL database
- [ ] Set up SSL certificates (Let's Encrypt)
- [ ] Configure email service (SendGrid, AWS SES, etc.)

## Security Features Enabled
- ✅ Brute force protection (django-axes)
- ✅ Session security (HTTP-only, secure cookies)
- ✅ SSL/HTTPS forced
- ✅ HSTS enabled
- ✅ XSS protection
- ✅ Content sniffing protection
- ✅ Clickjacking protection
- ✅ CSRF protection
- ✅ Masked admin URL
- ✅ Email verification required
- ✅ Strong password validation

## Monitoring
- [ ] Set up error logging (Sentry)
- [ ] Configure database backups
- [ ] Set up server monitoring
- [ ] Enable security notifications

## Performance
- [ ] Enable Redis for caching
- [ ] Configure database connection pooling
- [ ] Set up CDN for static files
- [ ] Enable gzip compression