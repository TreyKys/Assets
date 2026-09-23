using System;
using System.CodeDom.Compiler;
using System.ComponentModel;
using System.ComponentModel.DataAnnotations;
using System.Runtime.CompilerServices;
using System.Threading;
using Newtonsoft.Json;

namespace BVB.EOS.OnlineBanking.UI.Mobile.Services.ApiServices.App.Contracts;

[GeneratedCode("NJsonSchema", "14.4.0.0 (NJsonSchema v11.3.2.0 (Newtonsoft.Json v13.0.0.0))")]
public class AttachmentDto : INotifyPropertyChanged
{
	private Guid a;

	private string b;

	private string c;

	private string d;

	private string e;

	private long? f;

	private byte[] g;

	private DateTime h;

	private DateTime? i;

	private bool j;

	[CompilerGenerated]
	private PropertyChangedEventHandler k;

	[JsonProperty("attachmentID", Required = Required.DisallowNull, NullValueHandling = NullValueHandling.Ignore)]
	[Required(AllowEmptyStrings = true)]
	public Guid AttachmentID
	{
		get
		{
			short num = 22758;
			short num2 = num;
			num = 22758;
			switch (num2 == num)
			{
			default:
				num = 0;
				if (num != 0)
				{
				}
				num = 1;
				if (num != 0)
				{
				}
				return a;
			}
		}
		set
		{
			short num = 0;
			int num2 = num;
			while (true)
			{
				switch (num2)
				{
				case 0:
					switch (0)
					{
					case 0:
						goto IL_0036;
					}
					break;
				default:
					goto IL_0036;
				case 1:
					a = value;
					RaisePropertyChanged("AttachmentID");
					num = 2;
					num2 = num;
					break;
				case 2:
					return;
					IL_0036:
					num = 1;
					if (num != 0)
					{
					}
					if (a != value)
					{
						num = -18730;
						short num3 = num;
						num = -18730;
						switch (num3 == num)
						{
						case false:
						case true:
							break;
						default:
							goto IL_00bb;
						}
						goto case 0;
					}
					return;
					IL_00bb:
					num = 0;
					if (num != 0)
					{
					}
					num = 1;
					num2 = num;
					break;
				}
			}
		}
	}

	[JsonProperty("fileName", Required = Required.Default, NullValueHandling = NullValueHandling.Ignore)]
	public string FileName
	{
		get
		{
			short num = 1;
			if (num != 0)
			{
			}
			num = -17427;
			short num2 = num;
			num = -17427;
			switch (num2 == num)
			{
			default:
				num = 0;
				if (num != 0)
				{
				}
				return b;
			}
		}
		set
		{
			short num = 2;
			int num2 = num;
			while (true)
			{
				switch (num2)
				{
				case 2:
					switch (0)
					{
					default:
						goto end_IL_0026;
					case 0:
						break;
					}
					goto default;
				default:
					if (b != value)
					{
						num = 0;
						num2 = num;
						break;
					}
					return;
				case 0:
				{
					num = 1;
					if (num != 0)
					{
					}
					num = 21546;
					short num3 = num;
					num = 21546;
					switch (num3 == num)
					{
					default:
						num = 0;
						if (num != 0)
						{
						}
						b = value;
						RaisePropertyChanged("FileName");
						num = 1;
						num2 = num;
						break;
					case false:
					case true:
						return;
					}
					break;
				}
				case 1:
					return;
					end_IL_0026:
					break;
				}
			}
		}
	}

	[JsonProperty("fileExtension", Required = Required.Default, NullValueHandling = NullValueHandling.Ignore)]
	public string FileExtension
	{
		get
		{
			short num = 3919;
			short num2 = num;
			num = 3919;
			switch (num2 == num)
			{
			default:
				num = 1;
				if (num != 0)
				{
				}
				num = 0;
				if (num != 0)
				{
				}
				return c;
			}
		}
		set
		{
			short num = 0;
			int num2 = num;
			while (true)
			{
				switch (num2)
				{
				case 0:
					switch (0)
					{
					default:
						goto end_IL_002b;
					case 0:
						break;
					}
					goto default;
				default:
					if (c != value)
					{
						num = 1;
						num2 = num;
						break;
					}
					return;
				case 1:
				{
					c = value;
					RaisePropertyChanged("FileExtension");
					num = 1;
					if (num != 0)
					{
					}
					num = -23832;
					short num3 = num;
					num = -23832;
					switch (num3 == num)
					{
					default:
						num = 0;
						if (num != 0)
						{
						}
						num = 2;
						num2 = num;
						break;
					case false:
					case true:
						return;
					}
					break;
				}
				case 2:
					return;
					end_IL_002b:
					break;
				}
			}
		}
	}

	[JsonProperty("fileSize", Required = Required.Default, NullValueHandling = NullValueHandling.Ignore)]
	public string FileSize
	{
		get
		{
			short num = -27836;
			short num2 = num;
			num = -27836;
			switch (num2 == num)
			{
			default:
				num = 0;
				if (num != 0)
				{
				}
				num = 1;
				if (num != 0)
				{
				}
				return d;
			}
		}
		set
		{
			while (true)
			{
				short num = 2;
				int num2 = num;
				while (true)
				{
					num = -13413;
					short num3 = num;
					num = -13413;
					switch (num3 == num)
					{
					case false:
					case true:
						break;
					default:
						num = 0;
						if (num != 0)
						{
						}
						switch (num2)
						{
						case 2:
							switch (0)
							{
							default:
								goto end_IL_008f;
							case 0:
								break;
							}
							goto default;
						default:
							if (d != value)
							{
								num = 1;
								num2 = num;
								break;
							}
							return;
						case 1:
							num = 1;
							if (num != 0)
							{
							}
							d = value;
							RaisePropertyChanged("FileSize");
							num = 0;
							num2 = num;
							break;
						case 0:
							return;
							end_IL_008f:
							break;
						}
						continue;
					}
					break;
				}
			}
		}
	}

	[Required(AllowEmptyStrings = true)]
	[JsonProperty("type", Required = Required.DisallowNull, NullValueHandling = NullValueHandling.Ignore)]
	public string Type
	{
		get
		{
			short num = 15107;
			short num2 = num;
			num = 15107;
			switch (num2 == num)
			{
			default:
				num = 0;
				if (num != 0)
				{
				}
				num = 1;
				if (num != 0)
				{
				}
				return e;
			}
		}
		set
		{
			while (true)
			{
				short num = 0;
				int num2 = num;
				while (true)
				{
					switch (num2)
					{
					case 0:
						switch (0)
						{
						default:
							continue;
						case 0:
							break;
						}
						goto default;
					default:
						if (e != value)
						{
							num = 2;
							num2 = num;
							continue;
						}
						break;
					case 2:
						e = value;
						RaisePropertyChanged("Type");
						num = 1;
						num2 = num;
						continue;
					case 1:
						num = 1;
						if (num == 0)
						{
						}
						break;
					}
					break;
				}
				num = 301;
				short num3 = num;
				num = 301;
				switch (num3 == num)
				{
				case false:
				case true:
					continue;
				}
				num = 0;
				if (num == 0)
				{
				}
				return;
			}
		}
	}

	[JsonProperty("documentArchiveNumber", Required = Required.Default, NullValueHandling = NullValueHandling.Ignore)]
	public long? DocumentArchiveNumber
	{
		get
		{
			short num = -31683;
			short num2 = num;
			num = -31683;
			switch (num2 == num)
			{
			default:
				num = 0;
				if (num != 0)
				{
				}
				num = 1;
				if (num != 0)
				{
				}
				return f;
			}
		}
		set
		{
			int num = default(int);
			long? num4 = default(long?);
			long? num5 = default(long?);
			switch (0)
			{
			default:
				while (true)
				{
					short num2;
					switch (num)
					{
					case 2:
						if (num4 == num5)
						{
							return;
						}
						goto IL_0066;
					case 0:
						f = value;
						RaisePropertyChanged("DocumentArchiveNumber");
						num2 = 1;
						num = num2;
						continue;
					case 1:
						{
							num2 = 17921;
							short num3 = num2;
							num2 = 17921;
							switch (num3 == num2)
							{
							case false:
							case true:
								break;
							default:
								num2 = 1;
								if (num2 != 0)
								{
								}
								num2 = 0;
								if (num2 == 0)
								{
								}
								return;
							}
							goto IL_0066;
						}
						IL_0066:
						num2 = 0;
						num = num2;
						continue;
					}
					break;
				}
				goto case 0;
			case 0:
			{
				num4 = f;
				num5 = value;
				short num2 = 2;
				num = num2;
				goto default;
			}
			}
		}
	}

	[JsonProperty("content", Required = Required.Default, NullValueHandling = NullValueHandling.Ignore)]
	public byte[] Content
	{
		get
		{
			short num = -11704;
			short num2 = num;
			num = -11704;
			switch (num2 == num)
			{
			default:
				num = 1;
				if (num != 0)
				{
				}
				num = 0;
				if (num != 0)
				{
				}
				return g;
			}
		}
		set
		{
			short num = 2;
			int num2 = num;
			while (true)
			{
				switch (num2)
				{
				case 2:
					switch (0)
					{
					default:
						goto end_IL_0025;
					case 0:
						break;
					}
					goto default;
				default:
					if (g != value)
					{
						num = 1;
						if (num != 0)
						{
						}
						num = 0;
						num2 = num;
						break;
					}
					return;
				case 0:
				{
					g = value;
					RaisePropertyChanged("Content");
					num = -11460;
					short num3 = num;
					num = -11460;
					switch (num3 == num)
					{
					default:
						num = 0;
						if (num != 0)
						{
						}
						num = 1;
						num2 = num;
						break;
					case false:
					case true:
						return;
					}
					break;
				}
				case 1:
					return;
					end_IL_0025:
					break;
				}
			}
		}
	}

	[Required(AllowEmptyStrings = true)]
	[JsonProperty("createDate", Required = Required.DisallowNull, NullValueHandling = NullValueHandling.Ignore)]
	public DateTime CreateDate
	{
		get
		{
			short num = -16258;
			short num2 = num;
			num = -16258;
			switch (num2 == num)
			{
			default:
				num = 1;
				if (num != 0)
				{
				}
				num = 0;
				if (num != 0)
				{
				}
				return h;
			}
		}
		set
		{
			short num = 2;
			int num2 = num;
			while (true)
			{
				num = 10248;
				short num3 = num;
				num = 10248;
				switch (num3 == num)
				{
				case false:
				case true:
					return;
				}
				num = 0;
				if (num != 0)
				{
				}
				switch (num2)
				{
				case 2:
					switch (0)
					{
					default:
						goto end_IL_008a;
					case 0:
						break;
					}
					goto default;
				default:
					if (h != value)
					{
						num = 1;
						num2 = num;
						break;
					}
					return;
				case 1:
					num = 1;
					if (num != 0)
					{
					}
					h = value;
					RaisePropertyChanged("CreateDate");
					num = 0;
					num2 = num;
					break;
				case 0:
					return;
					end_IL_008a:
					break;
				}
			}
		}
	}

	[JsonProperty("attachmentAvailableUntil", Required = Required.Default, NullValueHandling = NullValueHandling.Ignore)]
	public DateTime? AttachmentAvailableUntil
	{
		get
		{
			short num = 13723;
			short num2 = num;
			num = 13723;
			switch (num2 == num)
			{
			default:
				num = 1;
				if (num != 0)
				{
				}
				num = 0;
				if (num != 0)
				{
				}
				return i;
			}
		}
		set
		{
			int num = default(int);
			DateTime? dateTime = default(DateTime?);
			DateTime? dateTime2 = default(DateTime?);
			switch (0)
			{
			default:
				while (true)
				{
					switch (num)
					{
					case 4:
						if (dateTime.HasValue != dateTime2.HasValue)
						{
							short num2 = 6;
							num = num2;
						}
						else
						{
							short num2 = 8;
							num = num2;
						}
						continue;
					case 5:
					{
						i = value;
						RaisePropertyChanged("AttachmentAvailableUntil");
						short num2 = 3;
						num = num2;
						continue;
					}
					case 3:
						return;
					case 2:
					{
						short num2 = 7;
						num = num2;
						continue;
					}
					case 6:
					{
						short num2 = -29794;
						short num3 = num2;
						num2 = -29794;
						switch (num3 == num2)
						{
						case false:
						case true:
							return;
						}
						num2 = 0;
						if (num2 != 0)
						{
						}
						num2 = 1;
						num = num2;
						continue;
					}
					case 1:
					{
						short num2 = 5;
						num = num2;
						continue;
					}
					case 0:
						if (!(dateTime.GetValueOrDefault() != dateTime2.GetValueOrDefault()))
						{
							return;
						}
						goto case 1;
					case 8:
					{
						short num2 = 1;
						if (num2 != 0)
						{
						}
						if (dateTime.HasValue)
						{
							num2 = 0;
							num = num2;
						}
						else
						{
							num2 = 2;
							num = num2;
						}
						continue;
					}
					case 7:
						return;
					}
					break;
				}
				goto case 0;
			case 0:
			{
				dateTime = i;
				dateTime2 = value;
				short num2 = 4;
				num = num2;
				goto default;
			}
			}
		}
	}

	[JsonProperty("isAttachmentAvailable", Required = Required.DisallowNull, NullValueHandling = NullValueHandling.Ignore)]
	public bool IsAttachmentAvailable
	{
		get
		{
			short num = 2056;
			short num2 = num;
			num = 2056;
			switch (num2 == num)
			{
			default:
				num = 1;
				if (num != 0)
				{
				}
				num = 0;
				if (num != 0)
				{
				}
				return j;
			}
		}
		set
		{
			short num = 0;
			int num2 = num;
			while (true)
			{
				switch (num2)
				{
				case 0:
					switch (0)
					{
					default:
						continue;
					case 0:
						break;
					}
					break;
				case 1:
				{
					num = 1;
					if (num != 0)
					{
					}
					num = 27354;
					short num3 = num;
					num = 27354;
					switch (num3 == num)
					{
					case false:
					case true:
						break;
					default:
						num = 0;
						if (num != 0)
						{
						}
						j = value;
						RaisePropertyChanged("IsAttachmentAvailable");
						num = 2;
						num2 = num;
						continue;
					}
					break;
				}
				case 2:
					return;
				}
				if (j != value)
				{
					num = 1;
					num2 = num;
					continue;
				}
				break;
			}
		}
	}

	public event PropertyChangedEventHandler PropertyChanged
	{
		[CompilerGenerated]
		add
		{
			int num = default(int);
			PropertyChangedEventHandler propertyChangedEventHandler = default(PropertyChangedEventHandler);
			PropertyChangedEventHandler propertyChangedEventHandler2 = default(PropertyChangedEventHandler);
			while (true)
			{
				switch (0)
				{
				default:
					while (true)
					{
						switch (num)
						{
						case 1:
							goto IL_0043;
						case 2:
							goto IL_011f;
						case 0:
							return;
						}
						break;
						IL_011f:
						short num2;
						if ((object)propertyChangedEventHandler == propertyChangedEventHandler2)
						{
							num2 = 0;
							num = num2;
							continue;
						}
						goto IL_00dd;
						IL_00dd:
						propertyChangedEventHandler2 = propertyChangedEventHandler;
						PropertyChangedEventHandler propertyChangedEventHandler3 = (PropertyChangedEventHandler)Delegate.Combine(propertyChangedEventHandler2, value);
						propertyChangedEventHandler = Interlocked.CompareExchange(ref k, propertyChangedEventHandler3, propertyChangedEventHandler2);
						num2 = 2;
						num = num2;
						continue;
						IL_0043:
						num2 = -3413;
						short num3 = num2;
						num2 = -3413;
						switch (num3 == num2)
						{
						case false:
						case true:
							break;
						default:
							goto IL_008b;
						}
						goto end_IL_0001;
						IL_008b:
						num2 = 1;
						if (num2 != 0)
						{
						}
						num2 = 0;
						if (num2 == 0)
						{
						}
						goto IL_00dd;
					}
					goto case 0;
				case 0:
					{
						propertyChangedEventHandler = k;
						short num2 = 1;
						num = num2;
						goto default;
					}
					end_IL_0001:
					break;
				}
			}
		}
		[CompilerGenerated]
		remove
		{
			int num = default(int);
			PropertyChangedEventHandler propertyChangedEventHandler = default(PropertyChangedEventHandler);
			switch (0)
			{
			default:
			{
				PropertyChangedEventHandler propertyChangedEventHandler2 = default(PropertyChangedEventHandler);
				while (true)
				{
					switch (num)
					{
					case 0:
					{
						propertyChangedEventHandler2 = propertyChangedEventHandler;
						PropertyChangedEventHandler propertyChangedEventHandler3 = (PropertyChangedEventHandler)Delegate.Remove(propertyChangedEventHandler2, value);
						propertyChangedEventHandler = Interlocked.CompareExchange(ref k, propertyChangedEventHandler3, propertyChangedEventHandler2);
						short num2 = 2;
						num = num2;
						continue;
					}
					case 2:
					{
						short num2 = -17602;
						short num3 = num2;
						num2 = -17602;
						switch (num3 == num2)
						{
						default:
							num2 = 0;
							if (num2 != 0)
							{
							}
							if ((object)propertyChangedEventHandler != propertyChangedEventHandler2)
							{
								break;
							}
							goto case false;
						case false:
						case true:
							num2 = 1;
							num = num2;
							continue;
						}
						goto case 0;
					}
					case 1:
						return;
					}
					break;
				}
				goto case 0;
			}
			case 0:
			{
				short num2 = 1;
				if (num2 != 0)
				{
				}
				propertyChangedEventHandler = k;
				num2 = 0;
				num = num2;
				goto default;
			}
			}
		}
	}

	protected virtual void RaisePropertyChanged([CallerMemberName] string propertyName = null)
	{
		int num = default(int);
		PropertyChangedEventHandler propertyChangedEventHandler = default(PropertyChangedEventHandler);
		switch (0)
		{
		default:
			while (true)
			{
				switch (num)
				{
				case 2:
					if (propertyChangedEventHandler != null)
					{
						short num2 = 0;
						num = num2;
						continue;
					}
					return;
				case 0:
				{
					short num2 = 1;
					if (num2 != 0)
					{
					}
					propertyChangedEventHandler(this, new PropertyChangedEventArgs(propertyName));
					num2 = -15938;
					short num3 = num2;
					num2 = -15938;
					switch (num3 == num2)
					{
					case false:
					case true:
						break;
					default:
						num2 = 0;
						if (num2 != 0)
						{
						}
						num2 = 1;
						num = num2;
						continue;
					}
					break;
				}
				case 1:
					return;
				}
				break;
			}
			goto case 0;
		case 0:
		{
			propertyChangedEventHandler = k;
			short num2 = 2;
			num = num2;
			goto default;
		}
		}
	}
}
