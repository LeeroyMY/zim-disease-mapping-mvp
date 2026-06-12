# Prototype Decommissioning Plan

After the clinical assessment and grading period is complete, the following steps must be taken to safely shut down the ZimEpi Tracker prototype:

1. **Revoke Credentials**: Delete or disable the demo `admin` and `user1` accounts.
2. **Rotate Secrets**: Invalidate the `SECRET_KEY` and any database passwords exposed during testing.
3. **Environment Variables**: Remove configuration variables from the Render and Supabase dashboards.
4. **Disable Services**: Pause or delete the web service on Render to halt internet accessibility.
5. **Data Deletion**: Archive the GitHub repository and permanently delete the synthetic data files if no longer needed.
6. **Documentation**: Ensure screenshots and evidence for the dissertation are preserved before disabling the live dashboards.

**Important Note**: No identifiable patient data was ever uploaded to this prototype. The system uses purely synthetic and randomized demonstration data.
