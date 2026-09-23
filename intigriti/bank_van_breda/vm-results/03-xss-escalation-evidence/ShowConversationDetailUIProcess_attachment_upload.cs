					case 0:
						if (num5 <= App.Services.Banking.Document.GetMaximumAttachmentSize())
						{
							string text = showConversationDetailUIProcess.m();
							this.m_d = new AttachmentDto
							{
								AttachmentID = Guid.NewGuid(),
								Content = showConversationDetailUIProcess.SelectOrScanDocumentUIProcess.FileContent,
								FileName = text,
								FileExtension = System.IO.Path.GetExtension(text).ToLower(),
								FileSize = showConversationDetailUIProcess.SelectOrScanDocumentUIProcess.FileContent.Length.ToString()
							};
							taskAwaiter2 = App.Services.Communication.CreateAttachment(this.m_d.ToFileInfo(), "MESSAGE").GetAwaiter();
							num = 6;
							num3 = num;
						}
